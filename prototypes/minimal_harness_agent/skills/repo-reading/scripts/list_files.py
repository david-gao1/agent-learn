from pathlib import Path


def main() -> None:
    for path in sorted(Path.cwd().rglob("*")):
        if path.is_file() and ".demo_state" not in path.parts:
            print(path)


if __name__ == "__main__":
    main()
