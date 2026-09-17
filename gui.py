import json
import os
import shutil
import socket
import subprocess
import tempfile
import tkinter as tk
import uuid
from tkinter import messagebox, ttk

import stats as estatisticas
from music_player_core.library import listar_musicas, pasta_musicas


class MusicPlayerGUI:
    INTERVALO_ATUALIZACAO_MS = 250

    def __init__(self, janela):
        self.janela = janela
        self.janela.title("Music Player")
        self.janela.geometry("760x500")
        self.janela.minsize(520, 340)

        self.pasta_musicas = pasta_musicas()
        self.musicas = []
        self.processo = None
        self.socket_path = None
        self.arquivo_playlist = None
        self.rastreador = None
        self.indice_atual = None

        self._montar_interface()
        self.atualizar_biblioteca()
        self.janela.protocol("WM_DELETE_WINDOW", self.fechar)
        self.janela.after(self.INTERVALO_ATUALIZACAO_MS, self._acompanhar)

    def _montar_interface(self):
        principal = ttk.Frame(self.janela, padding=16)
        principal.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            principal,
            text="Biblioteca",
            font=("TkDefaultFont", 16, "bold"),
        ).pack(anchor=tk.W)
        ttk.Label(
            principal,
            text=str(self.pasta_musicas),
        ).pack(anchor=tk.W, pady=(0, 10))

        quadro_lista = ttk.Frame(principal)
        quadro_lista.pack(fill=tk.BOTH, expand=True)

        barra = ttk.Scrollbar(quadro_lista, orient=tk.VERTICAL)
        self.lista = tk.Listbox(
            quadro_lista,
            activestyle="dotbox",
            exportselection=False,
            yscrollcommand=barra.set,
        )
        barra.config(command=self.lista.yview)
        self.lista.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        barra.pack(side=tk.RIGHT, fill=tk.Y)
        self.lista.bind("<Double-Button-1>", self.tocar)
        self.lista.bind("<Return>", self.tocar)

        self.texto_status = tk.StringVar(value="Nenhuma música em reprodução")
        ttk.Label(
            principal,
            textvariable=self.texto_status,
            anchor=tk.W,
        ).pack(fill=tk.X, pady=(12, 8))

        controles = ttk.Frame(principal)
        controles.pack(fill=tk.X)
        ttk.Button(controles, text="Tocar", command=self.tocar).pack(
            side=tk.LEFT
        )
        self.botao_pausa = ttk.Button(
            controles,
            text="Pausar",
            command=self.alternar_pausa,
        )
        self.botao_pausa.pack(side=tk.LEFT, padx=8)
        ttk.Button(controles, text="Avançar", command=self.avancar).pack(
            side=tk.LEFT
        )
        ttk.Button(
            controles,
            text="Atualizar biblioteca",
            command=self.atualizar_biblioteca,
        ).pack(side=tk.RIGHT)

    def atualizar_biblioteca(self):
        if self.processo is not None and self.processo.poll() is None:
            messagebox.showinfo(
                "Reprodução em andamento",
                "Encerre e abra novamente o GUI para recarregar a biblioteca "
                "durante uma reprodução.",
            )
            return
        selecao = self.lista.curselection()
        selecionada = self.musicas[selecao[0]] if selecao else None
        try:
            self.musicas = listar_musicas(self.pasta_musicas)
        except OSError as erro:
            messagebox.showerror(
                "Biblioteca indisponível",
                f"Não foi possível ler a biblioteca:\n{erro}",
            )
            return

        self.lista.delete(0, tk.END)
        for musica in self.musicas:
            self.lista.insert(tk.END, os.path.splitext(musica)[0])

        if selecionada in self.musicas:
            indice = self.musicas.index(selecionada)
            self.lista.selection_set(indice)
            self.lista.see(indice)
        elif self.musicas:
            self.lista.selection_set(0)

        if not self.musicas:
            self.texto_status.set("Nenhuma música encontrada")

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
            messagebox.showerror(
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
            messagebox.showerror(
                "Erro ao iniciar",
                f"Não foi possível iniciar o mpv:\n{erro}",
            )
            return

        self.rastreador = estatisticas.RastreadorReproducao()
        self.indice_atual = None
        self.texto_status.set("Iniciando reprodução…")

    def tocar(self, _evento=None):
        if not self.musicas:
            return
        selecao = self.lista.curselection()
        indice = selecao[0] if selecao else 0

        if self.processo is not None and self.processo.poll() is None:
            self._comando_mpv(["set_property", "playlist-pos", indice])
            self._comando_mpv(["set_property", "pause", False])
            return
        self._iniciar_mpv(indice)

    def alternar_pausa(self):
        if self.processo is None or self.processo.poll() is not None:
            return
        self._comando_mpv(["cycle", "pause"])

    def avancar(self):
        if self.processo is None or self.processo.poll() is not None:
            self.tocar()
            return
        self._comando_mpv(["playlist-next", "force"])

    def _acompanhar(self):
        if self.processo is not None:
            if self.processo.poll() is not None:
                self._finalizar_rastreamento()
                self._limpar_recursos()
                self.texto_status.set("Reprodução encerrada")
            else:
                posicao = self._propriedade("playlist-pos")
                tempo_atual = self._propriedade("time-pos")
                duracao = self._propriedade("duration")
                pausada = self._propriedade("pause")
                if posicao is not None:
                    try:
                        indice = int(posicao)
                        musica = self.musicas[indice]
                    except (IndexError, TypeError, ValueError):
                        musica = None
                    if musica is not None:
                        if indice != self.indice_atual:
                            self.lista.selection_clear(0, tk.END)
                            self.lista.selection_set(indice)
                            self.lista.see(indice)
                            self.indice_atual = indice
                        self.rastreador.atualizar(
                            musica,
                            tempo_atual,
                            duracao,
                            pausada,
                        )
                        estado = "Pausado" if pausada else "Tocando"
                        self.texto_status.set(
                            f"{estado}: {os.path.splitext(musica)[0]}"
                        )
                        self.botao_pausa.config(
                            text="Continuar" if pausada else "Pausar"
                        )
        self.janela.after(self.INTERVALO_ATUALIZACAO_MS, self._acompanhar)

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
                except FileNotFoundError:
                    pass
                except OSError:
                    pass
        self.socket_path = None
        self.arquivo_playlist = None
        self.botao_pausa.config(text="Pausar")

    def fechar(self):
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
        self.janela.destroy()


def main():
    try:
        janela = tk.Tk()
    except tk.TclError as erro:
        print(f"Não foi possível abrir a interface gráfica: {erro}")
        return 1
    MusicPlayerGUI(janela)
    janela.mainloop()
    return 0


def cli():
    return main()


if __name__ == "__main__":
    raise SystemExit(cli())
