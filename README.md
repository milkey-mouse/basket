# basket

Did you know that egg is one of the most popular types of child to eat?
Manage and control all of your cybernetic eggs with Basket™.

# Dependencies

- [Python 3](https://python.org/)
- [OpenCV](https://opencv.org/) version 3
- [mjpg-streamer](https://github.com/jacksonliam/mjpg-streamer) with the `input_opencv.so` plugin:

      mkdir build && cd build
      cmake -DPLUGIN_INPUT_OPENCV=ON ..
      make && sudo make install

- [Flask](http://flask.pocoo.org/)
- [Nginx](https://nginx.org/en/)

# Setup

- Basket was designed to run on a Raspberry Pi with an [official](https://www.amazon.com/dp/B01ER2SKFS) or [unofficial](https://www.amazon.com/dp/B00N1YJKFS) (recommended) Pi Camera in our custom [Basket Case™](hw/README.md).
  The default interface to the Pi Camera (where userspace uses MMAL directly) is not compatible with OpenCV or the mjpg-streamer plugin. To make a long story short, you can make the Pi Camera act as a normal webcam by loading the Video4Linux driver:

      sudo raspi-config # enable the Pi Camera
      # make sure it will use the v4l driver
      sudo modprobe bcm2835-v4l2
      sudo sh -c 'echo bcm2835-v4l2 >> /etc/modules'
