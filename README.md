# MetroClock
 Neopixels to track Tyne & Wear Metro train times.

## Why?

The Tyne & Wear Metro is a theoretically wonderful service, however at 'roughly every 12 minutes' it's not a frequent service by light rail standards. At the time of writing all but one train on the network dates from when the system was built, in the 1980s; train reliability is very poor. Consequently, it's far from unusual to find a 30-minute gap in service.

While the Metro does publish a mobile app with current train updates, it's fairly clunky and requires multiple taps to display information, and updates are triggered manually. Also, in a pre-coffee state I find it challenging to convert minutes-until-next-train information into actual times by which I'd need to leave the house. Add in marshalling children heading to different schools, and it seemed worth investing in some tooling for my morning routine.

## What it does

`main.py` fetches upcoming train times for my chosen station and platform from the public JSON API, parses out the expected 'platform time', and builds a list of future trains. For those within 57 minutes of the current time, it extracts the number of minutes past the hour, maps that to a string of NeoPixels wrapped around a clock face, and lights up red splobs to represent the expected trains. When the minute hand points to the red splob, I've uncontroversially missed the train.

Why 57 minutes? Because the pixel strip I'm using is edge-lit and heavily diffused. It's not *completely* clear where the light is centred (which is fine - uncertainty around train time is represented by physical fuzziness. Also: oooh pretty). If a train appears close to the minute hand it's not clear if that's a train that's about to depart, or one that's an hour from now. Simply removing the far-future trains close to the current position of the minute hand removes the ambiguity.

If an update fails, the train dots are drawn in blue rather than red. At least, they should be. The API was up and down when I was building this, but it hasn't broken since I built out the error handling. I have no idea if that code actually works.

The URL we're working off:

https://metro-rti.nexus.org.uk/api/times/WTL/1

Helper functions can retrieve station names and platform information via API calls; these are in place but commented out for deployment.

## Hardware

The system is built around a [Pimoroni Plasma Stick 2040 W](https://shop.pimoroni.com/products/plasma-stick-2040-w) driving a [very pretty edge-lit diffused pixel strip](https://shop.pimoroni.com/products/neon-like-rgb-led-strip-with-diffuser-neopixel-ws2812-sk6812-compatible), with 96 LEDs/metre. This particular Plasma Stick may have been discontinued, but there's a [new version running on RP2350](https://shop.pimoroni.com/products/plasma-2350-w) which should behave similarly. Alternatively, any old Pi Pico should work – the Plasma Sticks just have convenient connectors.

The host clock happens to have a circumference of 1m (well, near enough – it's within about 1%), which is good because LED strip tends to come in 1m lengths. I used sticky dots to fix the pixel strip to the clock, which was initially a temporary thing but seems good enough for now. I foolishly positioned the strip recessed from the edge of the clock bezel, which needs fixing as it's possible for trains to be hidden behind the curve of the clock.

## Future developments / TODO

- I only need the information for morning commutes, so the system should stop pulling updates and turn the display off after, say, 08:30 and until 07:00. At the moment I'm physically unplugging it when I leave the house.
- Logging actual train arrival times might help clarify whether the train I typically want to catch actually happens or not. I have a QuestDB server running elsewhere on my home network, this should be straightforward.
- Rather than turning off during the day, perhaps show sunrise/sunset times? In the depths of winter I find it encouraging to see the rate at which the day lengthens.
- Alternatively/additionally: I live near the coast. Perhaps display a visualisation of tide times?
- Display mode could be hooked up to an MQTT channel, so the clock output could be controlled remotely.
- ...and then hang that off Homebridge so we can talk to the clock. Because obviously.

## Notes on handling times in MicroPython.

Wow, this seems to be a disaster area. Certainly, I spent far too long trying to make anything work. Anything at all.

The Pi Pico W has an RTC, which can be (and, here, is) set to sync to [waves hands vaguely] something, once a network connection is made. Converting times is not, however, as straightforward as one expects.

`RTC` reports time tuples in a sequence passed down from some specific hardware implementation some times ago; the internal `time.now()` call returns a different a similar tuple but in a different order; `datetime` isn't available; converting tuples using `mktime()` seems to fail if the tuple is passed between functions first (?!). Ugh.

My solution here is to:

1. Extract whichever bits of data are useful from the generated timestamp tuple.
2. Convert the tuple to seconds-since-epoch using `mktime()`, at point of collection.
3. Pass these data as ints, and never faff about with time tuples again.

The [official docs](https://docs.micropython.org/en/latest/library/time.html#time.mktime) suggest `mktime()` should work from a constructed tuple of ints; this isn't the case in my testing. The common suggestion is that [one is re-assigning a `time` variable somewhere](https://stackoverflow.com/questions/36041628/having-trouble-converting-a-date-string-to-a-unix-timestamp), but I'm not. There are some [useful notes in the Pi forums](https://forums.raspberrypi.com/viewtopic.php?t=369642).