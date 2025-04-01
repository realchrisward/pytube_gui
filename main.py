from pytubefix import YouTube
from PyQt6 import QtWidgets, uic, QtCore
import sys
import ffmpeg
import os




class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi("pytube_gui.ui",self)
        self.reset_gui()


    def reset_gui(self):
        self.yt_url = ""
        # self.yt_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        self.youtube_video_url_lineEdit.setText(self.yt_url)
        self.vid_options = []
        self.aud_options = []
        self.prog_options = []
        self.action_load()
        
        self.load_pushButton.clicked.connect(self.action_load)
        self.reset_pushButton.clicked.connect(self.reset_gui)
        self.progressive_download_pushButton.clicked.connect(self.action_prog_download)
        self.audio_only_pushButton.clicked.connect(self.action_audio_download)
        self.video_only_pushButton.clicked.connect(self.action_video_download)
        self.video_and_audio_pushButton.clicked.connect(self.action_audio_video_download)


    def action_load(self):
        self.yt_url = self.youtube_video_url_lineEdit.text()
        if self.yt_url == "":
            return
        else:
            try:
                print('starting')
                #self.yt = YouTube(self.yt_url, use_oauth=True, allow_oauth_cache=True)
                self.yt = YouTube(self.yt_url, use_oauth=True, allow_oauth_cache=True)
                print('object created')
                self.timer = QtCore.QTimer(self)
                self.timer.setSingleShot(True)
                self.timer.timeout.connect(self.action_continue_load)
                self.timer.start(1000)

            except:
                return

    def action_continue_load(self):
            print('...more loading...')
            print(f'{self.yt.streams.count} - streams')
            print('filtering streams')
            self.prog_options = self.yt.streams.filter(progressive=True)
            self.vid_options = self.yt.streams.filter(only_video=True)
            self.aud_options = self.yt.streams.filter(only_audio=True)
            print('getting suggested filename')
            self.filename = self.yt.streams[0].default_filename
            self.filename_lineEdit.setText(self.filename)
            print('preparing combobox')
            self.video_options_comboBox.clear()
            self.audio_options_comboBox.clear()
            self.progressive_options_comboBox.clear()

            self.video_options_comboBox.addItems([f'{i.itag}: {i.resolution} x {i.fps}fps, {i.codecs}' for i in self.vid_options])
            self.audio_options_comboBox.addItems([f'{i.itag}: {i.abr}, {i.codecs}' for i in self.aud_options])
            self.progressive_options_comboBox.addItems([f'{i.itag}: {i.resolution} x {i.fps}fps, {i.codecs}' for i in self.prog_options])


    def action_prog_download(self):
        self.status_pushButton.setText('...Busy...')
        self.filename = self.filename_lineEdit.text()
        self.output_path = self.output_path_lineEdit.text()
        self.selected_stream = self.yt.streams.get_by_itag(self.progressive_options_comboBox.currentText().split(':')[0])
        self.selected_stream.download(output_path = self.output_path, filename = self.filename)
        self.status_pushButton.setText('Ready')


    def action_video_download(self):
        self.status_pushButton.setText('...Busy...')
        self.filename = "video_"+self.filename_lineEdit.text()
        self.output_path = self.output_path_lineEdit.text()
        self.selected_stream = self.yt.streams.get_by_itag(self.video_options_comboBox.currentText().split(':')[0])
        self.selected_stream.download(output_path = self.output_path, filename = self.filename)
        self.status_pushButton.setText('Ready')


    def action_audio_download(self):
        self.status_pushButton.setText('...Busy...')
        print('downloading audio')
        self.filename = "audio_"+self.filename_lineEdit.text()
        self.output_path = self.output_path_lineEdit.text()
        self.selected_stream = self.yt.streams.get_by_itag(self.audio_options_comboBox.currentText().split(':')[0])
        self.selected_stream.download(output_path = self.output_path, filename = self.filename)
        self.status_pushButton.setText('Ready')


    def action_audio_video_download(self):
        self.status_pushButton.setText('...Busy...')
        print('downloading video')  
        self.action_audio_download()
        self.action_video_download()
        audio_path = os.path.join(self.output_path, "audio_"+self.filename_lineEdit.text())
        video_path = os.path.join(self.output_path, "video_"+self.filename_lineEdit.text())
        print(f"audio_path: {audio_path}\n{os.path.exists(audio_path)}")
        print(f"video_path: {video_path}\n{os.path.exists(video_path)}")
        input_audio = ffmpeg.input(audio_path)
        input_video = ffmpeg.input(video_path)
        ffmpeg.concat(input_video, input_audio, v=1, a=1).output(os.path.join(self.output_path,self.filename_lineEdit.text())).run()
        self.status_pushButton.setText('Ready')



def main():
    app = QtWidgets.QApplication(sys.argv)

    window = MainWindow()
    window.show()

    app.exec()

if __name__ == "__main__":
    main()
