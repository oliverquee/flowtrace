import argparse


def build_greeting(name: str) -> str:
    return f"Hello, {name}"


def print_greeting(message: str) -> None:
    print(message)


def run_hello(args: argparse.Namespace) -> None:
    message = build_greeting(args.name)
    print_greeting(message)


def run_fail(_args: argparse.Namespace) -> None:
    raise RuntimeError("cli_case fail command requested")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="FlowTrace CLI sample")
    subparsers = parser.add_subparsers(dest="command", required=True)

    hello_parser = subparsers.add_parser("hello")
    hello_parser.add_argument("--name", required=True)
    hello_parser.set_defaults(handler=run_hello)

    fail_parser = subparsers.add_parser("fail")
    fail_parser.set_defaults(handler=run_fail)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
