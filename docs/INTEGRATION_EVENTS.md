# Integration events

The SQLite outbox provides a durable handoff between edge inference and a
larger truck or fleet platform. Payloads follow
`schemas/integration-event.schema.json`.

## Event types

| Event | Meaning |
|---|---|
| `litter.object.confirmed` | The tracker confirmed an observed object candidate |
| `litter.review.completed` | A human confirmed, corrected, or rejected a classification |
| `litter.run.completed` | An inference run ended with its observed counts |
| `litter.collection.confirmed` | An external workflow positively confirmed physical collection |

Only `litter.collection.confirmed` represents collected material.

## Delivery workflow

Retrieve pending events:

```http
GET /v1/integration/events?limit=100
```

Send each payload to the fleet platform using the operator's authenticated
transport. After the remote system durably accepts an event, acknowledge it:

```http
POST /v1/integration/events/{event_id}/ack
```

Unacknowledged events remain available after process, network, or vehicle power
interruption. Consumers should use `event_id` as an idempotency key.

The API is local-only by default and does not provide authentication. A fleet
deployment must put authentication, authorization, encryption, retry limits,
and remote retention in the integration layer.
