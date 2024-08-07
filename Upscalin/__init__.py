import Upscalin.Resources as UpscalinResources
from Broken import BrokenProject

UPSCALIN = BrokenProject(
    PACKAGE=__file__,
    APP_NAME="Upscalin",
    APP_AUTHOR="BrokenSource",
    RESOURCES=UpscalinResources,
)

import sys
import time
from collections import deque
from pathlib import Path
from subprocess import PIPE
from typing import Annotated, Deque, List

import magic
import tqdm
import typer
from attr import Factory, define
from PIL import Image

from Broken import BrokenApp, BrokenThread, log, pydantic_cli
from Broken.Externals.FFmpeg import BrokenFFmpeg
from Broken.Externals.Upscaler import BrokenUpscaler, Realesr, Waifu2x
from Broken.Loaders.LoaderImage import LoadableImage

UPSCALIN_ABOUT = """
🍷A Convenience Multi-Upscalers for Video, GIF, Images. Batch Processing, Multithreaded
• Tip: run "upscalin --help" for More Options ✨

©️ Broken Source Software, AGPL-3.0-only License.
"""

@define
class Box:
    index: int
    frame: Image

@define
class Upscalin(BrokenApp):
    upscalers: Deque[BrokenUpscaler] = Factory(deque)
    mime: magic.Magic = Factory(lambda: magic.Magic(mime=True))
    threads: int = 5

    def add_upscaler(self, upscaler: BrokenUpscaler):
        self.upscalers.append(upscaler)

    def main(self) -> None:
        self.typer.description = UPSCALIN_ABOUT
        self.typer.command(self.input)
        self.typer.command(self.config)

        with self.typer.panel("⭐️ Upscalers"):
            self.typer.command(pydantic_cli(Realesr(), post=self.add_upscaler), name="realesr", naih=True)
            self.typer.command(pydantic_cli(Waifu2x(), post=self.add_upscaler), name="waifu2x", naih=True)

        self.typer.app.info.chain = True
        self.typer(sys.argv[1:])

    def config(self,
        threads: Annotated[int, typer.Option("--threads", "-t", min=1, help="Number of Threads to use for Upscaling")]
    ) -> None:
        self.threads = threads

    def input(self,
        input:  Annotated[Path, typer.Option("--input",  "-i", help="Input File (Image, Video, GIF) or Directory to Upscale")],
        output: Annotated[Path, typer.Option("--output", "-o", help="Output File or Directory to Save the Upscaled content")]=None,
    ) -> List[Path]:
        if (not self.upscalers):
            raise RuntimeError("At least one upscaler is required")

        artifacts = []

        # Default output to data directory
        output = (output or UPSCALIN.DIRECTORIES.DATA)

        for ifile in (input.iterdir()) if input.is_dir() else [input]:
            ofile = (output/ifile.name) if output.is_dir() else output
            mime = self.mime.from_file(ifile)

            log.info(f"Upscaling file ({mime} @ {ifile}) → ({ofile})")

            if mime.startswith("video") or mime.startswith("image/gif"):
                artifacts.append(self._upscale_video(ifile, ofile))
            elif mime.startswith("image"):
                artifacts.append(image := self._upscale_image(ifile))
                image.save(ofile, quality=95)

        return artifacts

    def _upscale_image(self, input: LoadableImage, *, echo: bool=True) -> Image:
        for upscaler in self.upscalers:
            input = upscaler.upscale(input, echo=echo, single_core=True)
        return input

    def _upscale_video(self, input: Path, output: Path) -> Path:
        total_frames  = BrokenFFmpeg.get_video_total_frames(input, echo=False)
        width, height = BrokenFFmpeg.get_video_resolution(input, echo=False)
        duration      = BrokenFFmpeg.get_video_duration(input, echo=False)
        framerate     = (total_frames/duration)

        # Find the final upscaled resolution
        for upscaler in self.upscalers:
            width, height = upscaler.output_size(width, height)

        # Raw copy original audio to a raw pipe input
        ffmpeg = (BrokenFFmpeg(time=duration).quiet()
            .pipe_input(pixel_format="rgb24", width=width, height=height, framerate=framerate)
            .input(input)
            .copy_audio()
            .output(path=output)
        ).popen(stdin=PIPE, wrapper=True)

        # The progress bar will synchronize the threads
        progress_bar = tqdm.tqdm(
            total=total_frames,
            desc=f"Upscaling Video @ ({width}x{height})",
            dynamic_ncols=True,
            unit=" Frames",
            maxinterval=0.1,
            mininterval=1/30,
            smoothing=0,
        )

        # Waits until our time to write the frame
        def upscale_thread(box: Box):
            frame = self._upscale_image(box.frame, echo=False)
            while progress_bar.n < box.index:
                time.sleep(1/100)
            ffmpeg.stdin.write(frame.tobytes())
            progress_bar.update()

        # Note: Creating a thread per frame is ok, as upscaling takes a lot
        for index, frame in enumerate(BrokenFFmpeg.iter_video_frames(input)):
            BrokenThread.new(
                target=upscale_thread,
                box=Box(index=index, frame=frame),
                pool=str(id(self)),
                max=self.threads,
            )

        # Wait for all threads to finish
        BrokenThread.pool(str(id(self))).join()
        progress_bar.close()
        ffmpeg.stdin.close()
        return output
