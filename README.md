# MetroClock
 Neopixels to track Tyne & Wear metro train times


The URL we're working off:

https://metro-rti.nexus.org.uk/api/times/WTL/1


## Notes on handling times in MicroPython.

Wow, this is a disaster area. `RTC` reports time tuples in a sequence passed down from some specific hardware implementations some times ago; `datetime` isn't available; converting tuples using `mktime()` seems to fail if the tuple is passed between functions first. Ugh.

My solution here is to:

1. Extract whichever bits of data are useful from the generated timestamp tuple.
2. Convert the tuple to seconds-since-epoch using `mktime()`, at point of collection.
3. Pass these data as ints, and never faff about with time tuples again.

The [official docs](https://docs.micropython.org/en/latest/library/time.html#time.mktime) suggest `mktime()` should work from a tuple of ints; this isn't the case in my testing. The common suggestion is that [one is re-assigning a `time` variable somewhere](https://stackoverflow.com/questions/36041628/having-trouble-converting-a-date-string-to-a-unix-timestamp), but I'm not. There are some [useful notes in the Pi forums](https://forums.raspberrypi.com/viewtopic.php?t=369642).

