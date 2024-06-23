import Upscalin.Resources as UpscalinResources
from Broken import BrokenProject

UPSCALIN = BrokenProject(
    PACKAGE=__file__,
    APP_NAME="Upscalin",
    APP_AUTHOR="BrokenSource",
    RESOURCES=UpscalinResources,
)

from Upscalin.Logic import Upscalin
