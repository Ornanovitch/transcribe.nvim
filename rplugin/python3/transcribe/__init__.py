import neovim
import mpv

from transcribe.util import (error, msg, fmtseconds) # noqa


@neovim.plugin
class Transcribe(object):
    def __init__(self, nvim):
        self.nvim = nvim

    def _mpv_log(self, loglevel, component, message):
        if (loglevel == 'error') or ('ERROR' in message):
            err_msg = '{}: {}'.format(component, message)
            error(self.nvim, err_msg)

    @neovim.function('_transcribe_load')
    def load_media(self, args):
        media = args[0]
        mode = args[1]

        if mode == 'audio':
            self.player = mpv.MPV(ytdl=True, video=False,
                                  log_handler=self._mpv_log)
            self.player.play(media)
        else:
            error(self.nvim, 'Wrong loading mode value')

        @self.player.event_callback('file-loaded')
        def echo_loaded(event):
            msg(self.nvim, 'media loaded')

        @self.player.event_callback('pause')
        def echo_pause(event):
            msg(self.nvim, 'playback paused')

        @self.player.event_callback('unpause')
        def echo_unpause(event):
            msg(self.nvim, 'playback resumed')

    @neovim.function('_transcribe_pause')
    def toggle_pause(self, args):
        self.player.cycle('pause')

    @neovim.function('_transcribe_speed')
    def set_speed(self, args):
        """Change playback speed

        Arguments:
        speed -- speed or increment
        mode  -- how to change speed (set, increase or decrease)
        """
        speed = args[0]
        mode = args[1]

        try:
            speed = round(float(speed), 1)
        except ValueError:
            error(self.nvim, 'argument should be a positive number')
            return

        if speed < 0:
            error(self.nvim, 'speed should a positive number')
            return

        if mode == 'set':
            self.player.speed = speed
        elif mode == 'inc':
            self.player.speed += speed
        elif mode == 'dec':
            if (self.player.speed - speed) >= 0.1:
                self.player.speed -= speed
            else:
                error(self.nvim, 'speed is already at minimum setting')
                return
        else:
            error(self.nvim, 'speed mode should be either set, inc or dec')

        info = 'playback speed set to {:1.1f}'.format(self.player.speed)
        msg(self.nvim, info)

    @neovim.function('_transcribe_seek')
    def seek(self, args):
        """Seek forward or backward

        Arguments:
        seek_target -- nonzero integer (nb of seconds)
        """
        # Wait for media file to be properly loaded
        self.player.wait_for_property('time-pos')

        seek_target = args[0]

        try:
            seek_target = int(seek_target)
        except ValueError:
            error(self.nvim, 'argument should be an integer')
            return

        if seek_target == 0:
            error(self.nvim, 'argument should be a nonzero integer')
            return

        self.player.seek(seek_target)

        @self.player.event_callback('seek')
        def echo_seek(event, seek_target=seek_target):
            if seek_target > 0:
                direction = 'forward'
            else:
                direction = 'backward'

            seek_msg = 'seek {} {} seconds'.format(direction, seek_target)
            msg(self.nvim, seek_msg)

    @neovim.function('_transcribe_get_timepos', sync=True)
    def get_timepos(self, args):
        """Get formatted time position in current file

        Arguments:
        format -- format string with {H}, {M}, {S}
        """
        # Wait for media file to be properly loaded
        self.player.wait_for_property('time-pos')

        fmt = args[0] if args else '[{H}:{M}:{S}] '
        return fmtseconds(self.player.time_pos, fmt)

    @neovim.function('_transcribe_progress')
    def msg_progress(self, args):
        """Display message with position in current file"""
        # Wait for media file to be properly loaded
        self.player.wait_for_property('time-pos')

        time_pos = fmtseconds(self.player.time_pos)
        perc_pos = round(self.player.percent_pos)

        msg_time_pos = 'progress: {} ({}%)'.format(time_pos, perc_pos)
        msg(self.nvim, msg_time_pos)
