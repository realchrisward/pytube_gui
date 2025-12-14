
__version__ = "0.2.0"
__program_name__ = "Youtube Downloader Helper"

from PySide6.QtCore import QFile, QObject, QThread, Signal
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QApplication, QFileDialog, QMainWindow
import ffmpeg
import logging
import os
from pathlib import Path
import sys
import yt_dlp

class LogEmitter(QObject):
    """
    LogEmitter is used by QTextEditLogger to enable access to
    QObject Signal for emitting to and
    """

    log = Signal(str)


class QTextEditLogger(logging.Handler):
    """
    QTextEditLogger serves as a logging handler to display logging messages
    within the GUI if running the client in interactive mode
    """

    def __init__(self, text_edit_widget):
        super().__init__()
        self.widget = text_edit_widget
        self.widget.setReadOnly(True)
        self.widget.setStyleSheet("background-color: lightgray;")

        self.log_emitter = LogEmitter()
        self.log_emitter.log.connect(self.widget.insertHtml)

    def emit(self, record):
        msg = self.format(record)
        # color code messages
        if "| INFO |" in msg:
            msg = f'<span style="color:black">{msg}</span><br>'
        elif "| DEBUG |" in msg:
            msg = f'<span style="color:green">{msg}</span><br>'
        elif "| WARNING |" in msg:
            msg = f'<span style="color:red">{msg}</span><br>'
        elif "| ERROR |" in msg:
            msg = f'<span style="color:red"><strong>{msg}</strong></span><br>'
        else:
            msg = f'<span style="color:black"><strong>{msg}</strong></span><br>'
        self.log_emitter.log.emit(msg)
        self.widget.verticalScrollBar().setSliderPosition(
            self.widget.verticalScrollBar().maximum()
        )

def main():
    loader = QUiLoader()
    global app
    app = QApplication()

    ui_file = QFile(os.path.join(os.path.dirname(__file__), "main_gui.ui"))
    ui = loader.load(ui_file)

    window = MainWindow(__program_name__+__version__, ui, app)
    window.ui.show()
    print("running")
    exit_code = app.exec()
    print(window.exit_status)
        
    sys.exit(exit_code)


class DownloadWorker(QThread):
    error = Signal(str)

    def __init__(self, ydl_opts, url, logger):
        super().__init__()
        self.ydl_opts = ydl_opts
        self.url = url
        self.logger = logger

    def run(self):
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                ydl.download([self.url])
        except Exception as e:
            self.error.emit(str(e))
        self.logger.info("finished")


class MainWindow(QMainWindow):
    def __init__(self, version, ui,  app):
        super().__init__()
        
        self.app = app
        self.ui = ui 
        self.version = version

        self.exit_status = "running"

        # migrate ui children to parent level of class
        # !!! note this creates some odd behavior when closing the window
        # calls to self.close will not succeed, but self.ui.close will
        # it looks like not all of the attributes/methods are linked, some are 
        # pseudo copied.
        for att, val in ui.__dict__.items():
            setattr(self, att, val)

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logging_format = logging.Formatter(
            "%(asctime)s | %(name)s | %(levelname)s | %(message)s\n"
        )
        self.logging_text_browser = QTextEditLogger(self.textEdit_status_window)
        self.logging_text_browser.setFormatter(self.logging_format)
        self.logging_text_browser.setLevel(logging.DEBUG)
        self.logger.addHandler(self.logging_text_browser)

        # test logging output
        self.logger.debug(version)

        self.setWindowTitle(f"{self.version}")
        self.label_window_title.setText(f"{version}")

        self.pushButton_reset.clicked.connect(self.action_reset)
        self.pushButton_download.clicked.connect(self.action_download)
        self.pushButton_output_path.clicked.connect(self.action_output_path)

    def action_output_path(self):
        self.label_output_path.setText(
            QFileDialog.getExistingDirectory(self, "select output directory", str(Path.home()))
        )
        self.logger.info(self.label_output_path.text())


    def action_reset(self):
        self.lineEdit_youtube_url.setText("")
        self.label_output_path.setText("")
        self.logger.info("--RESET--")
        
    def my_hook(self, d):
            if d['status'] == 'finished':
                self.logger.info(f"Done downloading {Path(d['filename']).name}")
            elif d['status'] == 'downloading':
                percent = d.get('_percent_str', '').strip()
                if percent != self._last_percent:
                    self._last_percent = percent
                    self.logger.info(
                        f"Downloading: {percent} | {d.get('_speed_str', '?')} | ETA {d.get('_eta_str', '?')}"
                    )

    def postprocessor_hook(self,d):
        status = d.get("status")

        if status == "started":
            self.logger.info(f"Post-processing started: {d.get('postprocessor')}")
        elif status == "processing":
            self.logger.info(f"Post-processing: {d.get('postprocessor')}")
        elif status == "finished":
            self.logger.info("Post-processing finished")

    def action_download(self):
        self.logger.info(f"downloading: {self.lineEdit_youtube_url.text()}")

        if self.lineEdit_youtube_url.text() == "":
            self.logger.error("no url proveded - Aborting...")
            return
        
        # Define the URL of the video you want to download
        video_url = self.lineEdit_youtube_url.text()
        # Define the directory where you want to save the file
        if self.label_output_path == "":
            self.logger.error("no save location provided - Aborting...")
            return
        save_path = self.label_output_path.text()

        # Ensure the download directory exists
        if not os.path.exists(save_path):
            os.makedirs(save_path)

        # Optional: A function to monitor download progress
        self._last_percent = None

        


        if self.checkBox_audio_only.isChecked():
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": "%(title)s.%(ext)s",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "0",
                    }
                ],
                "noplaylist": True,
                'progress_hooks': [self.my_hook], 
                'postprocessor_hooks': [self.postprocessor_hook],  
            }
        else: 
            # Options dictionary
            ydl_opts = {
                'format': 'bestvideo+bestaudio/best', # Select best quality video and audio
                'merge_output_format': 'mp4',        # Merge into an mp4 file (requires FFmpeg)
                'outtmpl': os.path.join(save_path, '%(title)s.%(ext)s'), # Output template
                'noplaylist': True,                  # Only download the single video, not the whole playlist
                'progress_hooks': [self.my_hook],         # Add a progress hook for custom behavior (optional, see below)
                'postprocessor_hooks': [self.postprocessor_hook],  
                "postprocessors": [
                    {
                        "key": "FFmpegVideoConvertor",
                        "preferedformat": "mp4",
                    }
                ],
                "postprocessor_args": [
                        "-c:v", "copy",      # Do NOT re-encode video
                        "-c:a", "aac",       # Convert audio to AAC
                        "-b:a", "192k",      # High-quality audio bitrate
                    ],
            }


        # Run the downloader

        self.worker = DownloadWorker(ydl_opts, video_url, self.logger)
        self.worker.error.connect(lambda e: self.logger.error(e))
        self.worker.start()
        # try:
        #     with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        #         ydl.download([video_url])
        # except Exception as e:
        #     self.logger.error(f"\nAn error occurred: {e}")



if __name__ == "__main__":
    main()

