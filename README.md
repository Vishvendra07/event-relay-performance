# Event Relay Performance

Reproduce the same 60-event workload with one versus three workers, with a failed acknowledgment on every sixth event.

[Source](project.py) · [Demo evidence](evidence/summary.json) · [Verification](evidence/checks.json)

## Run locally

Requires Python 3.11+ and a running local checkout of Event Relay from the same release. Start it using its Compose commands, then get its localhost address with `docker compose port api 8000`.

```sh
docker compose up --detach --scale worker=1 worker
```

Run the following from this benchmark directory. `$RELAY_API` is the full localhost origin including the dynamically mapped port.

```sh
python project.py --api "$RELAY_API" --count 60 --concurrency 12 --fail-ack-every 6 > workers-1.json
```

Scale Event Relay to three workers with `docker compose up --detach --scale worker=3 worker` in the relay checkout and repeat the same workload. [One worker](evidence/workers-1.json) · [Three workers](evidence/workers-3.json)

```sh
python -m unittest discover -v
```

## Engineering decision

Compare end-to-end observed time to receipt under fixed polling and concurrency. Retain every row and label the sample and test setup.

This benchmark uses a local Docker host and client polling. Use it to explain worker behavior under this workload, not to project hosted capacity.



[Technology or project reference](https://docs.python.org/3/library/concurrent.futures.html)
