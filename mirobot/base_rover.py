import functools


class BaseRover:
    def __init__(self, mirobot):
        "docstring"
        self._mirobot = mirobot

    def repeat_decorator(fn):

        @functools.wraps(fn)
        def repeat_wrapper(self, *args, **kwargs):
            args_names = fn.__code__.co_varnames[:fn.__code__.co_argcount]
            args_dict = dict(zip(args_names, args))

            def get_arg(arg_name, default=None):
                if arg_name in args_dict:
                    return args_dict.get(arg_name)
                elif arg_name in kwargs:
                    return kwargs.get(arg_name)
                else:
                    return default

            repeat = get_arg('repeat', 1)

            output = []
            for i in range(repeat):
                output.extend(fn(self, *args, **kwargs))

            return output

        return repeat_wrapper

    @repeat_decorator
    def move_upper_left(self, repeat=1, wait=True):
        instruction = "W7"
        return self._mirobot.send_msg(instruction, wait=wait, terminator='\r\n')

    @repeat_decorator
    def move_upper_right(self, repeat=1, wait=True):
        instruction = "W9"
        return self._mirobot.send_msg(instruction, wait=wait, terminator='\r\n')

    @repeat_decorator
    def move_bottom_left(self, repeat=1, wait=True):
        instruction = "W1"
        return self._mirobot.send_msg(instruction, wait=wait, terminator='\r\n')

    @repeat_decorator
    def move_bottom_right(self, repeat=1, wait=True):
        instruction = "W3"
        return self._mirobot.send_msg(instruction, wait=wait, terminator='\r\n')

    @repeat_decorator
    def move_forward(self, repeat=1, wait=True):
        instruction = "W8"
        return self._mirobot.send_msg(instruction, wait=wait, terminator='\r\n')

    @repeat_decorator
    def move_backward(self, repeat=1, wait=True):
        instruction = "W2"
        return self._mirobot.send_msg(instruction, wait=wait, terminator='\r\n')

    @repeat_decorator
    def move_left(self, repeat=1, wait=True):
        instruction = "W4"
        return self._mirobot.send_msg(instruction, wait=wait, terminator='\r\n')

    @repeat_decorator
    def move_right(self, repeat=1, wait=True):
        instruction = "W6"
        return self._mirobot.send_msg(instruction, wait=wait, terminator='\r\n')

    @repeat_decorator
    def rotate_left(self, repeat=1, wait=True):
        instruction = "W10"
        return self._mirobot.send_msg(instruction, wait=wait, terminator='\r\n')

    @repeat_decorator
    def rotate_right(self, repeat=1, wait=True):
        instruction = "W11"
        return self._mirobot.send_msg(instruction, wait=wait, terminator='\r\n')
