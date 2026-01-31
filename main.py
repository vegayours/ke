import argparse
from config import Config


def main():
    parser = argparse.ArgumentParser(description="Knowledge Engine")
    parser.add_argument(
        "--config",
        "-c",
        default="config.toml",
        help="Path to the config file (default: config.toml)",
    )
    args = parser.parse_args()

    config = Config(args.config)

    print("Hello from knowledge engine!")


if __name__ == "__main__":
    main()
