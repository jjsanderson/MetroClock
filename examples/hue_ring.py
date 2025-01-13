import plasma
from plasma import plasma_stick
from time import sleep

NUM_LEDS = 96

led_strip = plasma.WS2812(NUM_LEDS, 0, 0, plasma_stick.DAT, color_order=plasma.COLOR_ORDER_GRB)
led_strip.start()


# The pixels are arranged in a ring, NUM_LEDS around the circle.
# Draw a hue ring
def hue_ring():
    for i in range(NUM_LEDS):
        led_strip.set_hsv(i, i / NUM_LEDS, 1.0, 0.8)
        print(led_strip.get(i))
    # led_strip.show()

if __name__ == "__main__":
    hue_ring()
    sleep(10)
