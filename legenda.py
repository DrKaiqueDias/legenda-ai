"""Gere legendas locais em SRT e VTT a partir de um arquivo de áudio ou vídeo."""

import argparse
from dataclasses import dataclass
import html
import json
import math
from numbers import Real
from pathlib import Path
import re
import sys
import textwrap

VERSION = "1.0.0"
MODELS = ("tiny", "base", "small", "medium", "large-v3")


@dataclass(frozen=True)
class Cue:
    start: int
    end: int
    text: str


def milliseconds(seconds):
    if isinstance(seconds, bool) or not isinstance(seconds, Real) or not math.isfinite(seconds) or seconds < 0:
        raise ValueError("O modelo retornou um tempo inválido.")
    return int(math.floor(seconds * 1000 + 0.5))


def timestamp(value, vtt=False):
    if type(value) is not int or value < 0:
        raise ValueError("O tempo precisa ser um inteiro não negativo em milissegundos.")
    hours, rest = divmod(value, 3600000)
    minutes, rest = divmod(rest, 60000)
    seconds, ms = divmod(rest, 1000)
    separator = "." if vtt else ","
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}{separator}{ms:03d}"


def clean_text(text):
    if not isinstance(text, str):
        raise ValueError("O modelo retornou texto inválido.")
    # Control characters must not create extra subtitle blocks or invalid files.
    return " ".join(re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text).split())


def subtitle_lines(text, width=42):
    """Prefer two balanced lines when a cue fits comfortably on screen."""
    text = clean_text(text)
    if len(text) <= width:
        return [text]
    words = text.split()
    candidates = [(abs(len(" ".join(words[:i])) - len(" ".join(words[i:]))), i)
                  for i in range(1, len(words))
                  if len(" ".join(words[:i])) <= width and len(" ".join(words[i:])) <= width]
    if candidates:
        _, split = min(candidates)
        return [" ".join(words[:split]), " ".join(words[split:])]
    return textwrap.wrap(text, width=width, break_long_words=False, break_on_hyphens=False)


def build_cues(segments, translated=False):
    cues = []

    def append(start, end, text):
        start, end = milliseconds(start), milliseconds(end)
        if end < start:
            raise ValueError("O modelo retornou um intervalo invertido.")
        text = clean_text(text)
        if not text:
            return
        # Preserve very short words even when millisecond rounding collapses a span.
        if end == start:
            end = start + 1
        # Word alignment can overlap by a few milliseconds. Never overlap cues.
        start = max(start, cues[-1].end if cues else 0)
        if end <= start:
            # Keep the text instead of silently dropping a fully overlapping word.
            if cues:
                previous = cues[-1]
                cues[-1] = Cue(previous.start, previous.end, previous.text + " " + text)
            return
        cues.append(Cue(start, end, text))

    for segment in segments:
        words = None if translated else getattr(segment, "words", None)
        if not words:
            append(segment.start, segment.end, segment.text)
            continue
        group = []
        for word in words:
            # Validate each word, including ones with no visible text.
            if milliseconds(word.end) < milliseconds(word.start):
                raise ValueError("O modelo retornou uma palavra com intervalo invertido.")
            candidate = "".join(w.word for w in group) + word.word
            if group and (len(clean_text(candidate)) > 80 or word.end - group[0].start > 6):
                append(group[0].start, group[-1].end, "".join(w.word for w in group))
                group = []
            group.append(word)
        if group:
            append(group[0].start, group[-1].end, "".join(w.word for w in group))
    return cues


def render(cues, kind):
    if kind not in ("srt", "vtt"):
        raise ValueError("Formato desconhecido.")
    blocks = []
    previous_end = 0
    for index, cue in enumerate(cues, 1):
        if (type(cue.start) is not int or type(cue.end) is not int
                or cue.start < previous_end or cue.end <= cue.start or not clean_text(cue.text)):
            raise ValueError("Legenda com texto ou intervalo inválido.")
        previous_end = cue.end
        lines = subtitle_lines(cue.text)
        payload = html.escape("\n".join(lines), quote=False)
        times = f"{timestamp(cue.start, kind == 'vtt')} --> {timestamp(cue.end, kind == 'vtt')}"
        blocks.append(f"{index}\n{times}\n{payload}")
    prefix = "WEBVTT\n\n" if kind == "vtt" else ""
    return prefix + "\n\n".join(blocks) + ("\n" if blocks else "")


def save_outputs(directory, cues, metadata):
    if not cues:
        raise ValueError("Nenhuma fala foi identificada. Nenhum arquivo foi criado.")
    contents = {
        "legendas.srt": render(cues, "srt"),
        "legendas.vtt": render(cues, "vtt"),
        "transcricao.txt": "\n".join(c.text for c in cues) + "\n",
        "informacoes.json": json.dumps(metadata, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
    }
    directory = Path(directory)
    # Exclusive directory creation prevents overwriting any previous work.
    directory.mkdir(parents=True, exist_ok=False)
    created = []
    try:
        for name, content in contents.items():
            target = directory / name
            with target.open("x", encoding="utf-8", newline="\n") as handle:
                created.append(target)
                handle.write(content)
    except BaseException:
        for target in created:
            target.unlink(missing_ok=True)
        directory.rmdir()
        raise


def transcribe(args, model_factory=None):
    source = Path(args.arquivo).expanduser().resolve()
    output = Path(args.saida).expanduser().resolve() if args.saida else source.with_name(source.stem + ".legendas")
    if not source.is_file():
        raise ValueError(f"Arquivo não encontrado: {source}")
    if source.stat().st_size == 0:
        raise ValueError("O arquivo está vazio.")
    if output.exists():
        raise ValueError(f"A pasta de saída já existe: {output}. Escolha outra com --saida.")
    if args.idioma != "auto" and not re.fullmatch(r"[a-z]{2,3}", args.idioma):
        raise ValueError("Use um código de idioma, como pt, en, es, ou auto.")
    if args.multilingue and args.idioma != "auto":
        raise ValueError("--multilingue deve ser usado com --idioma auto.")
    if model_factory is None:
        try:
            from faster_whisper import WhisperModel
        except ImportError as error:
            raise RuntimeError("Instale as dependências: python -m pip install -r requirements.txt") from error
        model_factory = WhisperModel
    print(f"Carregando o modelo {args.modelo}. Na primeira execução, o download pode demorar.", file=sys.stderr)
    model = model_factory(args.modelo, device="cpu", compute_type="int8",
                          download_root=str(Path(args.modelos).expanduser()),
                          local_files_only=args.offline)
    if args.idioma != "auto" and args.idioma not in model.supported_languages:
        raise ValueError(f"Idioma não suportado: {args.idioma}. Códigos: {', '.join(model.supported_languages)}")
    print("Ouvindo o arquivo e marcando os tempos...", file=sys.stderr)
    segments, info = model.transcribe(
        str(source), language=None if args.idioma == "auto" else args.idioma,
        task="translate" if args.ingles else "transcribe", beam_size=5,
        word_timestamps=not args.ingles, vad_filter=True,
        multilingual=args.multilingue, condition_on_previous_text=False,
    )
    cues = build_cues(segments, translated=args.ingles)
    metadata = {"versao": VERSION, "modelo": args.modelo, "idioma_detectado": info.language,
                "idioma_de_saida": "en" if args.ingles else ("multilingue" if args.multilingue else info.language),
                "tarefa": "traducao_para_ingles" if args.ingles else "transcricao",
                "trechos": len(cues), "execucao": "cpu/int8", "revisao_humana_recomendada": True}
    save_outputs(output, cues, metadata)
    return output, metadata


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("arquivo", help="Caminho do áudio ou vídeo; use aspas se houver espaços.")
    result.add_argument("--idioma", default="auto", help="Idioma falado: auto, pt, en, es, fr, ja...")
    result.add_argument("--modelo", choices=MODELS, default="base", help="base é o padrão; small costuma exigir mais tempo e memória.")
    result.add_argument("--saida", help="Nova pasta para as legendas; nunca sobrescreve uma pasta existente.")
    result.add_argument("--modelos", default=".modelos", help="Pasta de download e cache dos modelos.")
    result.add_argument("--offline", action="store_true", help="Usa somente modelos já baixados.")
    result.add_argument("--ingles", action="store_true", help="Traduz a fala para inglês, em vez de manter o idioma original.")
    result.add_argument("--multilingue", action="store_true", help="Detecta mudanças de idioma ao longo do arquivo.")
    result.add_argument("--version", action="version", version=VERSION)
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        output, metadata = transcribe(args)
    except KeyboardInterrupt:
        print("\nOperação interrompida.", file=sys.stderr)
        return 130
    except Exception as error:
        print(f"Não foi possível gerar a legenda: {error}", file=sys.stderr)
        return 1
    print(f"Pronto: {metadata['trechos']} trechos em {output}")
    print("Abra legendas.srt ou legendas.vtt no seu player/editor e revise antes de publicar.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
