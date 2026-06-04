from sample_project.worker import build_message


def main() -> None:
    message = build_message("FlowTrace")
    print(message)


if __name__ == "__main__":
    main()
