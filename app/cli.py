import argparse
import sys
from pathlib import Path
from app.services.converter import ConversionService


def handle_convert(args: argparse.Namespace) -> int:
    source_path = Path(args.file)
    if not source_path.exists():
        print(f"Error: File '{args.file}' tidak ditemukan.", file=sys.stderr)
        return 1

    service = ConversionService()
    try:
        with open(source_path, "rb") as f:
            out = service.convert_stream(file_obj=f, filename=source_path.name)

        if args.output:
            out_path = Path(args.output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(out.markdown, encoding="utf-8")
            print(
                f"✅ Berhasil: '{source_path.name}' dikonversi ke '{args.output}' "
                f"({len(out.markdown)} karakter)",
                file=sys.stderr,
            )
        else:
            sys.stdout.write(out.markdown)
            if not out.markdown.endswith("\n"):
                sys.stdout.write("\n")

        if out.warnings:
            for w in out.warnings:
                print(f"⚠️  Peringatan: {w}", file=sys.stderr)

        return 0
    except Exception as exc:
        print(f"❌ Gagal mengonversi '{source_path.name}': {exc}", file=sys.stderr)
        return 1


def handle_bundle(args: argparse.Namespace) -> int:
    service = ConversionService()
    file_streams = []

    for fpath in args.files:
        path = Path(fpath)
        if not path.exists():
            print(f"⚠️  Peringatan: File '{fpath}' dilewati (tidak ditemukan).", file=sys.stderr)
            continue
        try:
            stream = open(path, "rb")
            file_streams.append((stream, path.name, None))
        except Exception as e:
            print(f"⚠️  Peringatan: Gagal membuka '{fpath}': {e}", file=sys.stderr)

    if not file_streams:
        print("Error: Tidak ada file yang valid untuk di-bundle.", file=sys.stderr)
        return 1

    try:
        title = args.title or "Project Context"
        out = service.bundle_streams(files=file_streams, title=title)

        if args.output:
            out_path = Path(args.output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(out.markdown, encoding="utf-8")
            print(
                f"✅ Berhasil: {out.success_files}/{out.total_files} file digabung ke '{args.output}'",
                file=sys.stderr,
            )
        else:
            sys.stdout.write(out.markdown)
            if not out.markdown.endswith("\n"):
                sys.stdout.write("\n")

        if out.warnings:
            for w in out.warnings:
                print(f"⚠️  {w}", file=sys.stderr)

        return 0 if out.success_files > 0 else 1
    except Exception as exc:
        print(f"❌ Gagal memproses bundle: {exc}", file=sys.stderr)
        return 1
    finally:
        for stream, _, _ in file_streams:
            stream.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="file2md",
        description="File2MD CLI — Universal File-to-Markdown Converter (Local-First)",
    )
    subparsers = parser.add_subparsers(dest="command", help="Perintah yang tersedia")

    # Subcommand: convert
    p_convert = subparsers.add_parser("convert", help="Konversi file tunggal ke Markdown")
    p_convert.add_argument("file", help="Path ke file yang akan dikonversi (misal: doc.pdf, repo.zip)")
    p_convert.add_argument("-o", "--output", help="Path file output .md (opsional, default: stdout)")

    # Subcommand: bundle
    p_bundle = subparsers.add_parser("bundle", help="Gabungkan banyak file menjadi satu Markdown")
    p_bundle.add_argument("files", nargs="+", help="Daftar file yang akan digabungkan")
    p_bundle.add_argument("-o", "--output", help="Path file output .md (opsional, default: stdout)")
    p_bundle.add_argument("--title", help="Judul dokumen bundle (default: Project Context)")

    # Jika user tidak memasukkan argumen apapun, tampilkan help
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(0)

    args = parser.parse_args()

    if args.command == "convert":
        sys.exit(handle_convert(args))
    elif args.command == "bundle":
        sys.exit(handle_bundle(args))
    else:
        parser.print_help(sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()