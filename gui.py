import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import uuid

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import stats as estatisticas
from music_player_core.library import listar_musicas, pasta_musicas


class MusicPlayerGUI(QMainWindow):
    INTERVALO_ATUALIZACAO_MS = 250

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Music Player")
        self.resize(760, 500)
        self.setMinimumSize(520, 340)

        self.pasta_musicas = pasta_musicas()
        self.musicas = []
        self.processo = None
        self.socket_path = None
        self.arquivo_playlist = None
        self.rastreador = None
        self.indice_atual = None

        self._montar_interface()
        self.atualizar_biblioteca()

        self.temporizador = QTimer(self)
        self.temporizador.timeout.connect(self._acompanhar)
        self.temporizador.start(self.INTERVALO_ATUALIZACAO_MS)

    def _montar_interface(self):
        conteudo = QWidget(self)
        layout = QVBoxLayout(conteudo)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        titulo = QLabel("Biblioteca")
        fonte = titulo.font()
        fonte.setPointSize(16)
        fonte.setBold(True)
        titulo.setFont(fonte)
        layout.addWidget(titulo)
        layout.addWidget(QLabel(str(self.pasta_musicas)))

        self.lista = QListWidget()
        self.lista.itemDoubleClicked.connect(self.tocar)
        self.lista.itemActivated.connect(self.tocar)
        layout.addWidget(self.lista, 1)

        self.rotulo_status = QLabel("Nenhuma música em reprodução")
        layout.addWidget(self.rotulo_status)

        controles = QHBoxLayout()
        self.botao_tocar = QPushButton("Tocar")
        self.botao_tocar.clicked.connect(self.tocar)
        controles.addWidget(self.botao_tocar)

        self.botao_pausa = QPushButton("Pausar")
        self.botao_pausa.clicked.connect(self.alternar_pausa)
        controles.addWidget(self.botao_pausa)

        self.botao_avancar = QPushButton("Avançar")
        self.botao_avancar.clicked.connect(self.avancar)
        controles.addWidget(self.botao_avancar)
        controles.addStretch()

        self.botao_atualizar = QPushButton("Atualizar biblioteca")
        self.botao_atualizar.clicked.connect(self.atualizar_biblioteca)
        controles.addWidget(self.botao_atualizar)

        layout.addLayout(controles)
        self.setCentralWidget(conteudo)

    def atualizar_biblioteca(self, _evento=None):
        if self.processo is not None and self.processo.poll() is None:
            QMessageBox.information(
                self,
                "Reprodução em andamento",
                "Encerre e abra novamente o GUI para recarregar a biblioteca "
                "durante uma reprodução.",
            )
            return

        indice_selecionado = self.lista.currentRow()
        selecionada = (
            self.musicas[indice_selecionado]
            if 0 <= indice_selecionado < len(self.musicas)
            else None
        )
        try:
            self.musicas = listar_musicas(self.pasta_musicas)
        except OSError as erro:
            QMessageBox.critical(
                self,
                "Biblioteca indisponível",
                f"Não foi possível ler a biblioteca:\n{erro}",
            )
            return

        self.lista.clear()
        self.lista.addItems(
            [os.path.splitext(musica)[0] for musica in self.musicas]
        )

        if selecionada in self.musicas:
            self.lista.setCurrentRow(self.musicas.index(selecionada))
        elif self.musicas:
            self.lista.setCurrentRow(0)

        if not self.musicas:
            self.rotulo_status.setText("Nenhuma música encontrada")

    def _comando_mpv(self, comando):
        if not self.socket_path:
            return None
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conexao:
                conexao.settimeout(0.2)
                conexao.connect(self.socket_path)
                conexao.sendall(
                    json.dumps({"command": comando}).encode("utf-8") + b"\n"
                )
                resposta = conexao.recv(4096)
            return json.loads(resposta.decode("utf-8"))
        except (ConnectionError, OSError, json.JSONDecodeError):
            return None

    def _propriedade(self, nome):
        resposta = self._comando_mpv(["get_property", nome])
        return resposta.get("data") if resposta else None

    def _iniciar_mpv(self, indice):
        if shutil.which("mpv") is None:
            QMessageBox.critical(
                self,
                "mpv não encontrado",
                "Instale o mpv para usar o player gráfico.",
            )
            return

        identificador = f"{os.getpid()}-{uuid.uuid4().hex}"
        self.socket_path = os.path.join(
            tempfile.gettempdir(),
            f"music-player-gui-{identificador}.sock",
        )
        playlist = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".m3u8",
            encoding="utf-8",
            delete=False,
        )
        playlist.write("#EXTM3U\n")
        for musica in self.musicas:
            playlist.write(str(self.pasta_musicas / musica) + "\n")
        playlist.close()
        self.arquivo_playlist = playlist.name

        try:
            self.processo = subprocess.Popen(
                [
                    "mpv",
                    "--no-video",
                    "--audio-display=no",
                    "--cover-art-auto=no",
                    "--msg-level=all=error",
                    "--loop-playlist=inf",
                    f"--playlist-start={indice}",
                    f"--input-ipc-server={self.socket_path}",
                    f"--playlist={self.arquivo_playlist}",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError as erro:
            self._limpar_recursos()
            QMessageBox.critical(
                self,
                "Erro ao iniciar",
                f"Não foi possível iniciar o mpv:\n{erro}",
            )
            return

        self.rastreador = estatisticas.RastreadorReproducao()
        self.indice_atual = None
        self.rotulo_status.setText("Iniciando reprodução…")

    def tocar(self, _evento=None):
        if not self.musicas:
            return
        indice = self.lista.currentRow()
        if indice < 0:
            indice = 0

        if self.processo is not None and self.processo.poll() is None:
            self._comando_mpv(["set_property", "playlist-pos", indice])
            self._comando_mpv(["set_property", "pause", False])
            return
        self._iniciar_mpv(indice)

    def alternar_pausa(self, _evento=None):
        if self.processo is None or self.processo.poll() is not None:
            return
        self._comando_mpv(["cycle", "pause"])

    def avancar(self, _evento=None):
        if self.processo is None or self.processo.poll() is not None:
            self.tocar()
            return
        self._comando_mpv(["playlist-next", "force"])

    def _acompanhar(self):
        if self.processo is None:
            return
        if self.processo.poll() is not None:
            self._finalizar_rastreamento()
            self._limpar_recursos()
            self.rotulo_status.setText("Reprodução encerrada")
            return

        posicao = self._propriedade("playlist-pos")
        tempo_atual = self._propriedade("time-pos")
        duracao = self._propriedade("duration")
        pausada = self._propriedade("pause")
        if posicao is None:
            return

        try:
            indice = int(posicao)
            musica = self.musicas[indice]
        except (IndexError, TypeError, ValueError):
            return

        if indice != self.indice_atual:
            self.lista.setCurrentRow(indice)
            self.lista.scrollToItem(self.lista.item(indice))
            self.indice_atual = indice

        self.rastreador.atualizar(
            musica,
            tempo_atual,
            duracao,
            pausada,
        )
        estado = "Pausado" if pausada else "Tocando"
        self.rotulo_status.setText(
            f"{estado}: {os.path.splitext(musica)[0]}"
        )
        self.botao_pausa.setText("Continuar" if pausada else "Pausar")

    def _finalizar_rastreamento(self):
        if self.rastreador is not None:
            self.rastreador.finalizar()
            self.rastreador = None

    def _limpar_recursos(self):
        self.processo = None
        self.indice_atual = None
        for caminho in (self.socket_path, self.arquivo_playlist):
            if caminho:
                try:
                    os.unlink(caminho)
                except (FileNotFoundError, OSError):
                    pass
        self.socket_path = None
        self.arquivo_playlist = None
        self.botao_pausa.setText("Pausar")

    def closeEvent(self, evento):
        self.temporizador.stop()
        self._finalizar_rastreamento()
        if self.processo is not None and self.processo.poll() is None:
            try:
                self.processo.terminate()
                self.processo.wait(timeout=2)
            except (OSError, subprocess.TimeoutExpired):
                try:
                    self.processo.kill()
                except OSError:
                    pass
        self._limpar_recursos()
        evento.accept()


def main():
    aplicacao = QApplication.instance() or QApplication(sys.argv)
    janela = MusicPlayerGUI()
    janela.show()
    return aplicacao.exec()


def cli():
    return main()


if __name__ == "__main__":
    raise SystemExit(cli())
