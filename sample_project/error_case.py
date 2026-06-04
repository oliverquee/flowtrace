from worker import build_message


def prepare_error_message() -> str:
    return build_message("error case")


def explode() -> None:
    raise ValueError("sample runtime failure")


def main() -> None:
    message = prepare_error_message()
    print(message)
    explode()


if __name__ == "__main__":
    main()
