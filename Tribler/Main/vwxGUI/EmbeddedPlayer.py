# Written by Fabian van der Werf and Arno Bakker
# see LICENSE.txt for license information
#
# EmbeddedPlayerPanel is the panel used in Tribler 5.0
# EmbeddedPlayer4FramePanel is the panel used in the SwarmPlayer / 4.5
#

import wx
import os
import sys
import time

from threading import currentThread
from traceback import print_exc

from Tribler.__init__ import LIBRARYNAME
from Tribler.Video.defs import *
from Tribler.Video.VideoFrame import DelayTimer
from Tribler.Video.VideoPlayer import VideoPlayer
from Tribler.Main.vwxGUI.widgets import VideoProgress, FancyPanel, ActionButton, TransparentText, VideoVolume, VideoSlider
from Tribler.Main.vwxGUI import DEFAULT_BACKGROUND, forceWxThread, warnWxThread, SEPARATOR_GREY, GRADIENT_DGREY, GRADIENT_LGREY

DEBUG = True

class EmbeddedPlayerPanel(wx.Panel):
    """
    The Embedded Player consists of a VLCLogoWindow and the media controls such
    as Play/Pause buttons and Volume Control.
    """

    VIDEO_SIZE = (320,240)

    def __init__(self, parent, utility, vlcwrap, bg):
        wx.Panel.__init__(self, parent, -1)

        self.utility = utility
        self.parent = parent
        self.SetBackgroundColour(DEFAULT_BACKGROUND)

        self.volume = 0.48
        self.oldvolume = 0.48
        self.estduration = None
        self.fullscreenwindow = None
        self.download = None
        self.update = True
        self.timeoffset = None

        vSizer = wx.BoxSizer(wx.VERTICAL)

        self.vlcwrap = vlcwrap

        if vlcwrap:
            self.vlcwin = VLCLogoWindow(self, utility, vlcwrap, bg, animate = True)
            self.vlcwin.SetMinSize(EmbeddedPlayerPanel.VIDEO_SIZE)
    
            vSizer.Add(self.vlcwin, 1, wx.EXPAND, 0)
    
            self.ctrlpanel = FancyPanel(self, border = wx.TOP)
            self.ctrlpanel.SetMinSize((-1, 30))
            self.ctrlpanel.SetBorderColour(SEPARATOR_GREY)
            self.ctrlpanel.SetBackgroundColour(GRADIENT_LGREY, GRADIENT_DGREY)
    
            self.ctrlsizer = wx.BoxSizer(wx.HORIZONTAL)
    
            self.slider = VideoSlider(self.ctrlpanel)
            self.slider.Enable(False)
            self.timeposition = TransparentText(self.ctrlpanel, -1, "--:-- / --:--")
    
            self.bmp_muted = wx.Bitmap(os.path.join(self.utility.getPath(),LIBRARYNAME,"Main","vwxGUI","images","video_muted.png"))
            self.bmp_unmuted = wx.Bitmap(os.path.join(self.utility.getPath(),LIBRARYNAME,"Main","vwxGUI","images","video_unmuted.png"))
            self.mute = ActionButton(self.ctrlpanel, -1, self.bmp_unmuted)
            self.mute.Bind(wx.EVT_LEFT_UP, self.MuteClicked)
    
            self.bmp_pause = wx.Bitmap(os.path.join(self.utility.getPath(),LIBRARYNAME,"Main","vwxGUI","images","video_pause.png"))
            self.bmp_play = wx.Bitmap(os.path.join(self.utility.getPath(),LIBRARYNAME,"Main","vwxGUI","images","video_play.png"))
            self.ppbtn = ActionButton(self.ctrlpanel, -1, self.bmp_pause)
            self.ppbtn.Bind(wx.EVT_LEFT_UP, self.PlayPause)
            self.ppbtn.Enable(False)
    
            self.sbtn = ActionButton(self.ctrlpanel, -1, wx.Bitmap(os.path.join(self.utility.getPath(),LIBRARYNAME,"Main","vwxGUI","images","video_stop.png")))
            self.sbtn.Bind(wx.EVT_LEFT_UP, self.OnStop)
            self.sbtn.Enable(False)
    
            self.volctrl = VideoVolume(self.ctrlpanel, -1)
            self.volctrl.SetVolumeHandler(self.OnVolumeChanged)
            self.volctrl.SetValue(self.volume)
            self.volctrl.SetMinSize((30, 17))
    
            self.fsbtn = ActionButton(self.ctrlpanel, -1, wx.Bitmap(os.path.join(self.utility.getPath(),LIBRARYNAME,"Main","vwxGUI","images","video_fullscreen.png")))
            self.fsbtn.Bind(wx.EVT_LEFT_UP, self.FullScreen)
            self.fsbtn.Enable(False)

            self.ctrlsizer.AddSpacer((10, -1))
            self.ctrlsizer.Add(self.ppbtn, 0, wx.ALIGN_CENTER_VERTICAL|wx.TOP, 1)
            self.ctrlsizer.AddSpacer((10, -1))
            self.ctrlsizer.Add(self.sbtn, 0, wx.ALIGN_CENTER_VERTICAL|wx.TOP, 1)
            self.ctrlsizer.AddSpacer((10, -1))
            self.ctrlsizer.Add(self.slider, 1, wx.ALIGN_CENTER_VERTICAL)
            self.ctrlsizer.Add(self.timeposition, 0, wx.ALIGN_CENTER_VERTICAL)
            self.ctrlsizer.AddSpacer((10, -1))
    
            self.ctrlsizer.Add(self.mute, 0, wx.ALIGN_CENTER_VERTICAL|wx.TOP, 1)
            self.ctrlsizer.AddSpacer((5, -1))
            self.ctrlsizer.Add(self.volctrl, 0, wx.ALIGN_CENTER_VERTICAL|wx.TOP, 1)
            self.ctrlsizer.AddSpacer((10, -1))
            self.ctrlsizer.Add(self.fsbtn, 0, wx.ALIGN_CENTER_VERTICAL|wx.TOP, 1)
            self.ctrlsizer.AddSpacer((10, -1))
            
            self.ctrlpanel.SetSizer(self.ctrlsizer)
    
            vSizer.Add(self.ctrlpanel, 0, wx.ALIGN_BOTTOM|wx.EXPAND)

        self.SetSizer(vSizer)

        self.playtimer = None
        self.timer = None

        if self.vlcwrap:
            self.SetMinSize((EmbeddedPlayerPanel.VIDEO_SIZE[0],-1))
            self.vlcwin.Show(True)
            self.ctrlsizer.ShowItems(True)
            self.utility.guiUtility.frame.Layout()

    def OnVolumeChanged(self, volume):
        if self.mute.GetBitmapLabel() == self.bmp_muted: # unmute
            self.mute.SetBitmapLabel(self.bmp_unmuted, recreate = True)
        self.volume = volume
        self.oldvolume = self.volume
        self.SetVolume(self.volume)

    def MuteClicked(self, event):
        if self.mute.GetBitmapLabel() == self.bmp_muted:
            self.volume = self.oldvolume
        else:
            self.volume = 0

        self.volctrl.SetValue(self.volume)
        self.SetVolume(self.volume)
        self.mute.SetBitmapLabel(self.bmp_unmuted if self.mute.GetBitmapLabel() == self.bmp_muted else self.bmp_muted, recreate = True)

    @warnWxThread
    def Load(self, url, streaminfo = None):
        if DEBUG:
            print >> sys.stderr, "embedplay: Load:", url, streaminfo, currentThread().getName()

        if streaminfo is not None:
            self.estduration = streaminfo.get('estduration',None)
            self.download = VideoPlayer.getInstance().get_vod_download()

        # 19/02/10 Boudewijn: no self.slider when self.vlcwrap is None
        # 26/05/09 Boudewijn: when using the external player we do not have a vlcwrap
        if self.vlcwrap:
            self.slider.Enable(True)

            # Arno, 2009-02-17: If we don't do this VLC gets the wrong playlist somehow
            self.vlcwrap.stop()
            self.vlcwrap.playlist_clear()
            self.vlcwrap.load(url,streaminfo=streaminfo)
    
            # Enable update of progress slider
            wx.CallAfter(self.slider.SetValue, 0)
            if self.timer is None:
                self.timer = wx.Timer(self)
                self.Bind(wx.EVT_TIMER, self.UpdateSlider)
            self.timer.Start(500)

        self.fsbtn.Enable(True)
        self.ppbtn.Enable(True)
        self.sbtn.Enable(True)

    def StartPlay(self):
        """ Start playing the new item after VLC has stopped playing the old one """
        if DEBUG:
            print >>sys.stderr,"embedplay: PlayWhenStopped"

        self.playtimer = DelayTimer(self)

    @warnWxThread
    def Play(self, evt = None):
        if DEBUG:
            print >> sys.stderr, "embedplay: Play pressed"

        # Boudewijn, 26/05/09: when using the external player we do not have a vlcwrap
        if self.vlcwrap:
            if self.GetState() != MEDIASTATE_PLAYING:
                self.vlcwin.stop_animation()
                self.vlcwrap.start()
                self.ppbtn.SetBitmapLabel(self.bmp_pause, recreate = True)
            elif DEBUG:
                print >> sys.stderr, "embedplay: Play pressed, already playing"

    @warnWxThread
    def Pause(self, evt = None):
        if DEBUG:
            print >> sys.stderr, "embedplay: Pause pressed"

        # Boudewijn, 26/05/09: when using the external player we do not have a vlcwrap
        if self.vlcwrap:
            if self.GetState() == MEDIASTATE_PLAYING:
                self.vlcwrap.pause()
                self.ppbtn.SetBitmapLabel(self.bmp_play, recreate = True)
            elif DEBUG:
                print >> sys.stderr, "embedplay: Pause pressed, not playing"

    @warnWxThread
    def Resume(self, evt = None):
        if DEBUG:
            print >> sys.stderr, "embedplay: Resume pressed"

        if self.vlcwrap:
            if self.GetState() != MEDIASTATE_PLAYING:
                self.vlcwin.stop_animation()
                self.vlcwrap.resume()
                self.ppbtn.SetBitmapLabel(self.bmp_pause, recreate = True)

    @warnWxThread
    def PlayPause(self, evt = None):
        if DEBUG:
            print >> sys.stderr, "embedplay: PlayPause pressed"

        # Boudewijn, 26/05/09: when using the external player we do not have a vlcwrap
        if self.vlcwrap:
            self.vlcwrap.resume()
            self.ppbtn.SetBitmapLabel(self.bmp_play if self.ppbtn.GetBitmapLabel() == self.bmp_pause else self.bmp_pause, recreate = True)

    @warnWxThread
    def Seek(self, evt=None):
        if DEBUG:
            print >> sys.stderr, "embedplay: Seek"

        # Boudewijn, 26/05/09: when using the external player we do not have a vlcwrap
        if self.vlcwrap:
            position = self.slider.GetValue()
            self.update = False
    
            @forceWxThread
            def set_position():
                try:
                    self.vlcwrap.set_media_position_relative(position, self.GetState() == MEDIASTATE_STOPPED)

                    length = self.vlcwrap.get_stream_information_length()
                    length = length / 1000 if length > 0 else (self.estduration or self.download.get_vod_duration())
                    time_position = length * position
                    self.timeoffset = time_position - (self.vlcwrap.get_media_position() / 1000) 

                    self.update = True
                except:
                    print_exc()
                    if DEBUG:
                        print >> sys.stderr, 'embedplay: Could not seek'
    
            if self.download:
                self.download.set_vod_position(position, set_position)
            else:
                set_position()

    def FullScreen(self, evt=None):
        # Boudewijn, 26/05/09: when using the external player we do not have a vlcwrap
        if self.vlcwrap and self.fsbtn.IsEnabled():
            self._ToggleFullScreen()

    def OnFullScreenKey(self, event):
        if event.GetUnicodeKey() == wx.WXK_ESCAPE:
            self._ToggleFullScreen()

        elif event.GetUnicodeKey() == wx.WXK_SPACE:
            self._TogglePause()

    def _TogglePause(self):
        if self.GetState() == MEDIASTATE_PLAYING:
            self.vlcwrap.pause()
        else:
            self.vlcwrap.resume()

    @warnWxThread
    def _ToggleFullScreen(self):
        if isinstance(self.parent, wx.Frame): #are we shown in popup frame
            if self.ctrlsizer.IsShown(0): #we are not in fullscreen -> ctrlsizer is showing
                self.parent.ShowFullScreen(True)
                self.ctrlsizer.ShowItems(False)
                self.Layout()

                #Niels: 07-03-2012, only evt_close seems to work :(
                quitId = wx.NewId()
                pauseId = wx.NewId()
                self.parent.Bind(wx.EVT_MENU, lambda event: self._ToggleFullScreen(), id = quitId)
                self.parent.Bind(wx.EVT_MENU, lambda event: self._TogglePause(), id = pauseId)

                self.parent.Bind(wx.EVT_CLOSE, lambda event: self._ToggleFullScreen())
                self.parent.Bind(wx.EVT_LEFT_DCLICK, lambda event: self._ToggleFullScreen())

                accelerators = [(wx.ACCEL_NORMAL, wx.WXK_ESCAPE, quitId), (wx.ACCEL_CTRL, wx.WXK_SPACE, pauseId)]
                self.parent.SetAcceleratorTable(wx.AcceleratorTable(accelerators))
            else:
                self.parent.ShowFullScreen(False)
                self.ctrlsizer.ShowItems(True)
                self.Layout()

                self.parent.SetAcceleratorTable(wx.NullAcceleratorTable)
                self.parent.Unbind(wx.EVT_CLOSE)
        else:
            #saving media player state
            cur_time = self.vlcwrap.get_media_position()
            cur_state = self.vlcwrap.get_our_state()

            self.vlcwrap.stop()
            if not self.fullscreenwindow:
                # create a new top level frame where to attach the vlc widget and
                # render the fullscreen video
                self.fullscreenwindow = wx.Frame(None, title="FullscreenVLC")
                self.fullscreenwindow.SetBackgroundColour("BLACK")

                eventPanel = wx.Panel(self.fullscreenwindow)
                eventPanel.SetBackgroundColour(wx.BLACK)
                eventPanel.Bind(wx.EVT_KEY_DOWN, lambda event: self.OnFullScreenKey(event))
                self.fullscreenwindow.Bind(wx.EVT_CLOSE, lambda event: self._ToggleFullScreen())
                self.fullscreenwindow.ShowFullScreen(True)
                eventPanel.SetFocus()
                self.vlcwrap.set_window(self.fullscreenwindow)
            else:
                self.TellLVCWrapWindow4Playback()
                self.fullscreenwindow.Destroy()
                self.fullscreenwindow = None

            #restoring state
            if cur_state == MEDIASTATE_PLAYING:
                self.vlcwrap.start(cur_time)

            elif cur_state == MEDIASTATE_PAUSED:
                self.vlcwrap.start(cur_time)

                def doPause(cur_time):
                    self.vlcwrap.pause()
                    self.vlcwrap.set_media_position(cur_time)
                wx.CallLater(500, doPause, cur_time)

    def Save(self, evt = None):
        # save media content in different directory
        if self.save_button.isToggled():
            self.save_callback()

    def SetVolume(self, volume, evt = None):
        if DEBUG:
            print >> sys.stderr, "embedplay: SetVolume:", self.volume

        # Boudewijn, 26/05/09: when using the external player we do not have a vlcwrap
        if self.vlcwrap:
            self.vlcwrap.sound_set_volume(volume)

    def OnStop(self, event):
        if self.vlcwrap and self.sbtn.IsEnabled():
            self.Stop()
            self.sbtn.Enable(False)

    @forceWxThread
    def Stop(self):
        if DEBUG:
            print >> sys.stderr, "embedplay: Stop"

        # Boudewijn, 26/05/09: when using the external player we do not have a vlcwrap
        if self.vlcwrap:
            self.vlcwrap.stop()
            self.ppbtn.SetLabel(self.utility.lang.get('playprompt'))
            self.timeposition.SetLabel('--:-- / --:--')
            self.slider.SetValue(0)
            self.fsbtn.Enable(False)
            self.ppbtn.Enable(False)
            self.slider.Enable(False)
    
            if self.timer is not None:
                self.timer.Stop()

    def GetState(self):
        """ Returns the state of VLC as summarized by Fabian:
        MEDIASTATE_PLAYING, MEDIASTATE_PAUSED, MEDIASTATE_STOPPED """

        # Boudewijn, 26/05/09: when using the external player we do not have a vlcwrap
        if self.vlcwrap:
            status = self.vlcwrap.get_our_state()
            if DEBUG:
                print >> sys.stderr, "embedplay: GetState", status
    
            return status

        # catchall
        return MEDIASTATE_STOPPED

    def Reset(self):
        self.Stop()
        self.UpdateProgressSlider([])

    @forceWxThread
    def UpdateStatus(self, playerstatus, pieces_complete, vod_progress):
        self.SetPlayerStatus(playerstatus, vod_progress)
        if self.vlcwrap:
            self.UpdateProgressSlider(pieces_complete)

    def SetPlayerStatus(self, text, progress = None):
        if progress:
            self.SetProgress(progress)

    def SetContentName(self, s):
        self.vlcwin.set_content_name(s)

    def SetContentImage(self, wximg):
        self.vlcwin.set_content_image(wximg)

    def SetProgress(self, progress):
        self.vlcwin.loading.SetValue(progress)

    def UpdateProgressSlider(self, pieces):
        if self.vlcwrap:
            self.slider.SetBufferFromPieces(pieces)

    @warnWxThread
    def UpdateSlider(self, evt):
        # Boudewijn, 26/05/09: when using the external player we do not have a vlcwrap
        if self.vlcwrap and self.update:
            if self.GetState() != MEDIASTATE_STOPPED:
    
                length = self.vlcwrap.get_stream_information_length()
                length = length / 1000 if length > 0 else (self.estduration or self.download.get_vod_duration())
                cur = self.vlcwrap.get_media_position() / 1000
                if length and self.timeoffset:
                    cur += self.timeoffset

                if cur >= 0 and length:
                    self.slider.SetValue(cur / length)

                cur_str = self.FormatTime(float(cur)) if cur >= 0 else '--:--'
                length_str = self.FormatTime(length) if length else '--:--'
                self.timeposition.SetLabel('%s / %s' % (cur_str, length_str))
                self.ctrlsizer.Layout()

    def FormatTime(self, s):
        longformat = time.strftime('%d:%H:%M:%S', time.gmtime(s))
        if longformat.startswith('01:'):
            longformat = longformat[3:]
        while longformat.startswith('00:') and len(longformat) > len('00:00'):
            longformat = longformat[3:]
        return longformat

    def TellLVCWrapWindow4Playback(self):
        if self.vlcwrap:
            self.vlcwin.tell_vclwrap_window_for_playback()

    def ShowLoading(self):
        if self.vlcwrap:
            self.vlcwin.show_loading()


class VLCLogoWindow(wx.Panel):
    """ A wx.Window to be passed to the vlc.MediaControl to draw the video
    in (normally). In addition, the class can display a logo, a thumbnail and a
    "Loading: bla.video" message when VLC is not playing.
    """

    def __init__(self, parent, utility, vlcwrap, bg=wx.BLACK, animate = False, position = (300,300)):
        wx.Panel.__init__(self, parent)
        self.parent = parent ##

        self.utility = utility
        self.SetBackgroundColour(bg)
        self.bg = bg
        self.vlcwrap = vlcwrap

        self.contentname = None
        self.contentbm = None
        self.hsizermain = wx.BoxSizer(wx.HORIZONTAL)
        self.vsizer = wx.BoxSizer(wx.VERTICAL)

        if animate:
            self.loading = VideoProgress(self, -1)
            self.loading.Hide()
            self.loading.SetMinSize((300, 300))

            self.vsizer.Add(self.loading, 0, wx.CENTER|wx.RESERVE_SPACE_EVEN_IF_HIDDEN)
        else:
            self.loading = None

        self.hsizermain.Add(self.vsizer, 1, wx.CENTER)
        self.SetSizer(self.hsizermain)
        self.SetAutoLayout(1)
        self.Layout()

        if self.vlcwrap:
            wx.CallAfter(self.tell_vclwrap_window_for_playback)
        self.Refresh()

    def tell_vclwrap_window_for_playback(self):
        """ This method must be called after the VLCLogoWindow has been
        realized, otherwise the self.GetHandle() call that vlcwrap.set_window()
        does, doesn't return a correct XID.
        """
        self.vlcwrap.set_window(self)

    def get_vlcwrap(self):
        return self.vlcwrap

    def set_content_name(self,s):
        if DEBUG:
            print >>sys.stderr,"VLCWin: set_content_name"
        self.contentname = s
        self.Refresh()

    def set_content_image(self,wximg):
        if DEBUG:
            print >>sys.stderr,"VLCWin: set_content_image"
        if wximg is not None:
            self.contentbm = wx.BitmapFromImage(wximg,-1)
        else:
            self.contentbm = None

    def show_loading(self):
        if self.loading:
            self.logo = None
            self.loading.Show()
            self.Refresh()

    def stop_animation(self):
        if self.loading:
            self.loading.Hide()
            self.Refresh()

    def OnPaint(self,evt):
        dc = wx.PaintDC(self)
        dc.Clear()
        dc.BeginDrawing()

        x,y,maxw,maxh = self.GetClientRect()
        halfx = (maxw-x)/2
        halfy = (maxh-y)/2
        halfx = 10
        halfy = 10
        lheight = 20

        dc.SetPen(wx.Pen(self.bg,0))
        dc.SetBrush(wx.Brush(self.bg))
        if sys.platform == 'linux2':
            dc.DrawRectangle(x,y,maxw,maxh)

        dc.SetTextForeground(wx.WHITE)
        dc.SetTextBackground(wx.BLACK)

        lineoffset = 120
        txty = halfy+lheight+lineoffset
        if txty > maxh:
            txty = 0

        if self.contentbm is not None:
            bmy = max(20,txty-20-self.contentbm.GetHeight())
            dc.DrawBitmap(self.contentbm,30,bmy,True)

        dc.EndDrawing()
        if evt is not None:
            evt.Skip(True)
