import magic
from PIL import ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True

from Broken import *

UPSCALIN = BrokenProject(
    PACKAGE=__file__,
    APP_NAME="Upscalin",
    APP_AUTHOR="BrokenSource",
)

from Upscalin.Upscalin import *
