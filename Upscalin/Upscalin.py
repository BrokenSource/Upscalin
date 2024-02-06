from . import *

UPSCALIN_ABOUT = """
🍷A Convenience Multi-Upscalers for Video, Images. Batch Processing, Multithreaded
• Tip: run "upscalin --help" for More Options ✨

©️ 2023 Broken Source Software, AGPLv3-only License.
"""

@define
class Upscalin(BrokenApp):
    upscalers: list[BrokenUpscaler] = Factory(list)

    def cli(self):
        self.broken_typer = BrokenTyper(description=UPSCALIN_ABOUT, chain=True)
        self.broken_typer.command(self.waifu2x)
        self.broken_typer.command(self.esrgan)
        self.broken_typer.command(self.srmd)
        self.broken_typer.command(self.upscale, default=True)
        self.broken_typer(sys.argv[1:])

    def add(self, upscaler: BrokenUpscaler):
        log.info(f"Adding upscaler: {upscaler}")
        self.upscalers.append(upscaler)

    # Base upscalers

    def waifu2x(self, **kwargs):
        upscaler = BrokenWaifu2x()
        upscaler.__dict__.update(**kwargs)
        self.add(upscaler)

    def esrgan(self, **kwargs):
        self.add(BrokenEsrgan(**kwargs))

    def srmd(self, **kwargs):
        self.add(BrokenSrmd(**kwargs))

    # Upscalin methods

    def upscale(self,
        input:  Path,
        output: Path,
    ):
        ...
