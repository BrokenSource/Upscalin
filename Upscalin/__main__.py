import sys

from Broken import BrokenProfiler
from Upscalin import Upscalin


def main():
    with BrokenProfiler("UPSCALIN"):
        upscalin = Upscalin()
        upscalin.cli()

if __name__ == "__main__":
    main()
