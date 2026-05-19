
import sys
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from pygame import *
from mutagen.mp3 import MP3
from random import randint
import time




def om():
    app = QApplication(sys.argv)
    win = QWidget()
    
    p = QPalette()
    g = QLinearGradient(0,0,0,400)
    g.setColorAt(0.0, QColor(245,240,240))
    g.setColorAt(1.0, QColor(210,60,130))
    
    p.setBrush(QPalette.Window, QBrush(g))        

    def progress(stream, chunk, bytes_remaining,previousprogress = 0):
        
        total_size = stream.filesize
        bytes_download = total_size - bytes_remaining
        
        liveprogress = (int)(bytes_download / total_size * 100)
        if liveprogress > previousprogress:
            previousprogress = liveprogress
            p.setValue(liveprogress)
            print(liveprogress)
            
    def music():
        t = ["song1.mp3","song2.mp3","song3.mp3","song4.mp3","song5.mp3","song6.mp3","song7.mp3","song8.mp3"]
        computer = t[randint(0,7)]
        if b1.text() == "":
            b1.setIcon(QIcon("pause.png"))
            b1.setIconSize(QSize(100,70))
            b1.setText(".")
            mixer.init()
            mixer.music.load(t[0])
            #pygame.mixer.music.get_length()
            mixer.music.play()
            #move.start()
            song = MP3(t[0])
            songLength = song.info.length
            
            for i in range(100):
                time.sleep(2)
                bar.setValue(i)
            
            
            
            #for i in range(101):
             #   time.sleep(0.5)
              #  bar.setValue(i)
        
            
            
            
            #for i in 100:
            #    bar.setValue(100)
            #youtube = pytube.YouTube(t[0]) 
            #video = youtube.streams.first()  

            
            #yt = YouTube(t[0])
            #yt.register_on_progress_callback(progress)
            #yt.streams.filter(only_audio=True).first().download()
            
        elif b1.text() == ".":
            b1.setIcon(QIcon("play.png"))
            b1.setIconSize(QSize(100,70))
            mixer.init()
            mixer.music.pause()
            b1.setText("")
            #move.stop()
            
    def Lnext():
        t = ["song1.mp3","song2.mp3","song3.mp3","song4.mp3","song5.mp3","song6.mp3","song7.mp3","song8.mp3"]
        computer = t[randint(0,7)]
        mixer.init()
        
        if b1.text() == ".":
            mixer.init()
            mixer.music.load(t[1])
            mixer.music.play()
            b1.setText("!")
        elif b1.text() == "!":
            mixer.music.load(t[2])
            mixer.music.play()
            b1.setText("~")
        elif b1.text() == "~":
            mixer.music.load(t[3])
            mixer.music.play()               
            b1.setText(":")
        elif b1.text() == ":":
            mixer.music.load(t[4])
            mixer.music.play()
            b1.setText(";")
        elif b1.text() == ";":
            mixer.music.load(t[5])
            mixer.music.play()
            b1.setText(",")
        elif b1.text() == ",":
            mixer.music.load(t[6])
            mixer.music.play()
            b1.setText("|")
        elif b1.text() == "|":
            mixer.music.load(t[7])
            mixer.music.play()
            b1.setText("")            
            
    
    def Rnext():
        t = ["song1.mp3","song2.mp3","song3.mp3","song4.mp3","song5.mp3","song6.mp3","song7.mp3","song8.mp3"]
        computer = t[randint(0,7)]
        mixer.init()
        
        if b1.text() == "!":
            mixer.music.load(t[0])
            mixer.music.play()
            b1.setText("~")
        elif b1.text() == "~" or b1.text() == "!":
            mixer.music.load(t[1])
            mixer.music.play() 
            b1.setText(":")
        elif b1.text() == ":" or b1.text() == "~":
            mixer.music.load(t[2])
            mixer.music.play()
        elif b1.text() == ";":
            mixer.music.load(t[3])
            mixer.music.play()
        elif b1.text() == ",":
            mixer.music.load(t[4])
            mixer.music.play()
        elif b1.text() == "|":
            mixer.music.load(t[5])
            mixer.music.play()
        elif b1.text() == "":
            mixer.music.load(t[6])
            mixer.music.play()                       
                  
    l = QLabel(win)
    l.setFixedHeight(500)
    l.setFixedWidth(500)                                                           
    move = QMovie("disk.gif")
    l.setMovie(move)
    move.stop()    
    
    
    bar = QProgressBar(win)
    bar.setFixedHeight(9)
    bar.setStyleSheet("QProgressBar::chunk {background-color:red;}")
    bar.setFixedWidth(320)
    bar.move(70,550)
   
    
    
    
            
    b1 = QPushButton(win)
    b1.setFixedHeight(100)
    b1.setFixedWidth(100)
    b1.setIcon(QIcon("play.png"))
    b1.setIconSize(QSize(100,70))
    b1.setStyleSheet("QPushButton {border-radius:10px}")
    b1.move(180,600)
    b1.clicked.connect(music)
    #b1.clicked.connect(Lnext)
    #b1.clicked.connect(Rnext)
    
    pleft = QPushButton(win)
    pleft.setFixedHeight(100)
    pleft.setFixedWidth(100)
    pleft.setIcon(QIcon("left arrow.png"))
    pleft.setIconSize(QSize(100,70))
    pleft.setStyleSheet("QPushButton {border-radius:10px}")
    pleft.move(70,600)
    pleft.clicked.connect(Lnext)
    
    pright = QPushButton(win)
    pright.setFixedHeight(100)
    pright.setFixedWidth(100)
    pright.setIcon(QIcon("right arrow.png"))
    pright.setIconSize(QSize(100,70))
    pright.setStyleSheet("QPushButton {border-radius:10px}")
    pright.move(300,600)
    pright.clicked.connect(Rnext)
    
    win.setFixedHeight(800)
    win.setFixedWidth(450)
    win.setWindowTitle("Froz Player")
    #win.setPalette(p)
    win.setStyleSheet("QWidget {background -color : White}")
    win.show()
    sys.exit(app.exec_())
    
if __name__ == "__main__":
    om()    
s