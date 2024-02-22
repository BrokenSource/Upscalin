from . import *

UPSCALIN_ABOUT = """
🍷A Convenience Multi-Upscalers for Video, GIF, Images. Batch Processing, Multithreaded
• Tip: run "upscalin --help" for More Options ✨

©️ Broken Source Software, AGPLv3-only License.
"""

@define
class Upscalin(BrokenApp):
    upscalers: list[BrokenUpscaler] = Factory(list)
    mime:      magic.Magic          = Factory(lambda: magic.Magic(mime=True))

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
        self.add(BrokenRealEsrgan(**kwargs))

    def srmd(self, **kwargs):
        self.add(BrokenSrmd(**kwargs))

    # Upscalin methods

    def upscale(self,
        input:  Annotated[Path, TyperOption("-i", "--input",  help="Input File (Image, Video, GIF) or Directory to Upscale")],
        output: Annotated[Path, TyperOption("-o", "--output", help="Output File or Directory to Save the Upscaled content")]=None,
        thread: Annotated[int,  TyperOption("-t", "--thread", help="Number of Threads to use for Upscaling")]=5,
    ):
        for file in (input.iterdir()) if input.is_dir() else [input]:
            self.__upscale__(input=file, output=output, thread=thread)

    def __upscale_image__(self,
        input:  Union[Path, URL, Image],
        output: Union[Path, URL, None]=Image,
        *,
        thread: int=1,
        echo: bool=True,
        **ignore,
    ) -> Option[Path, Image]:

        # Chain upscalers
        for upscaler in self.upscalers:
            input = upscaler.upscale(input=input, output=Image, echo=echo)

        return input

    __video_frames__: Dict[int, Image] = {}

    def __upscale_video__(self,
        input:  Path,
        output: Path=None,
        *,
        thread: int=1,
        echo: bool=True,
        **ignore,
    ) -> Option[Path]:

        # Find Video properties
        total_frames = BrokenFFmpeg.get_total_frames(input, echo=False)
        resolution   = BrokenFFmpeg.get_resolution(input, echo=False)
        duration     = BrokenFFmpeg.get_video_duration(input, echo=False)
        framerate    = total_frames/duration

        # Find the final upscaled resolution
        for upscaler in self.upscalers:
            resolution = upscaler.output_size(*resolution)

        # Build the render command
        ffmpeg = (
            BrokenFFmpeg()
            .quiet()
            .overwrite()
            .format(FFmpegFormat.Rawvideo)
            .pixel_format(FFmpegPixelFormat.RGB24)
            .resolution(resolution)
            .framerate(framerate)
            .input("-")
            .audio_codec(FFmpegAudioCodec.Copy)
            .shortest()
            .video_codec(FFmpegVideoCodec.H264)
            .preset(FFmpegH264Preset.Slow)
            .tune(FFmpegH264Tune.Film)
            .quality(FFmpegH264Quality.High)
            .pixel_format(FFmpegPixelFormat.YUV420P)
            .output(output)
            .pipe()
        )

        # Get a progress bar
        progress_bar = tqdm.tqdm(
            total=total_frames,
            desc=f"Upscaling Video @ {resolution}",
            dynamic_ncols=True,
            unit=" Frames",
            maxinterval=1/10,
            smoothing=0,
        )

        def __upscale_image_thread__(index: int, frame):
            frame = self.__upscale_image__(input=frame, output=Image, echo=False)

            # Wait until our time to write the frame
            while progress_bar.n < index:
                time.sleep(1/100)

            # Write the frame
            ffmpeg.write(frame.tobytes())
            progress_bar.update()

        # Upscale each video frame
        for index, frame in enumerate(BrokenFFmpeg.get_frames(input)):
            BrokenThread.new(
                target=__upscale_image_thread__,
                frame=copy.copy(frame),
                index=index,
                pool=str(id(self)),
                max=thread,
            )

        # Finish processes
        progress_bar.close()
        ffmpeg.close()

        return output

    def __upscale__(self,
        input:  Path,
        output: Path=None,
        thread: int=1,
    ):
        # Get the file mime type
        mime = self.mime.from_file(input)

        # Easy: The input is a Image
        if mime.startswith("image"):
            return self.__upscale_image__(**BrokenUtils.locals())

        # Hard: The input is a Video or GIF
        if mime.startswith("video") or mime.startswith("image/gif"):
            return self.__upscale_video__(**BrokenUtils.locals())

