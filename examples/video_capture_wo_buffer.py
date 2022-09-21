import cv2, queue, threading, time

# bufferless VideoCapture
class VideoCapture:

  def __init__(self, name):
    self.cap = cv2.VideoCapture(1)
        
    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1600)
    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1200)
    self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 3)
    self.cap.set(cv2.CAP_PROP_AUTOFOCUS,0)
    self.cap.set(cv2.CAP_PROP_FOCUS, 150)

    self.q = queue.Queue()
    t = threading.Thread(target=self._reader)
    t.daemon = True
    t.start()

  # read frames as soon as they are available, keeping only most recent one
  def _reader(self):
    while True:
      ret, frame = self.cap.read()
      if not ret:
        break
      if not self.q.empty():
        try:
          self.q.get_nowait()   # discard previous (unprocessed) frame
        except Queue.Empty:
          pass
      self.q.put(frame)

  def read(self):
    return self.q.get()


if __name__ == "__main__":
    cap = VideoCapture(1)
    while True:
        frame = cap.read()
        time.sleep(.5)   # simulate long processing
        cv2.imshow("frame", frame)
        if chr(cv2.waitKey(1)&255) == 'q':
            break
