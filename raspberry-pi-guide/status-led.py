from gpiozero import LED
import socket

serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serversocket.bind(('localhost', 8089))
serversocket.listen(2)

led = LED(24)  # LED anode soldered to GPIO pin 24
led.blink(0.1, 1)  # Start with pattern equal to AWAITING_MTR

while True:
    connection, address = serversocket.accept()
    buf = connection.recv(64)
    if len(buf) > 0:
        if buf == b'AWAITING_MTR':
            led.blink(0.1, 1)
        elif buf == b'READING_MTR':
            led.blink(0.1, 0.5)
        elif buf == b'UPLOADING':
            led.blink(0.1, 0.1)
        elif buf == b'DONE':
            led.blink(2, 0.1)

