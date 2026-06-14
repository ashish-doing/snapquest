from ui_photo import demo
import tempfile

demo.queue().launch(
    show_api=False,
    allowed_paths=[tempfile.gettempdir(), "/tmp"],
    ssr_mode=False,
)