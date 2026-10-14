# Local Hermes memory

The Hermes stack runs Hindsight with embedded PostgreSQL and a local Ollama
server. Memory extraction and reflection use `hermes_hindsight_llm_model`
(`qwen3.5:2b-q4_K_M` by default). Embeddings and reranking run inside Hindsight with
multilingual models. No cloud LLM credentials are needed. Initial provisioning
downloads container images, the Ollama model, and the embedding/reranking models.
Subsequent inference runs locally.

The Ollama model pull completes before Hindsight starts. The gateway waits for
Hindsight's health check. Neither service publishes a host port; Hermes connects
to `http://hindsight:8888` over the Compose network.

The s6 init hook mounted at `/etc/cont-init.d/03-hindsight-plugins` runs after
Hermes' user setup and profile reconciliation, before gateways and the dashboard
start. It drops privileges to the remapped Hermes user and installs the reviewed
Hindsight plugin revision and its Python dependencies for every configured
profile. Installation is repeated at the same revision on container startup to
repair dependencies after image changes. A failed hook aborts startup. The Hermes
image is updated to v0.22.0 for its current catalog/dependency installation CLI.

Each profile activates `memory.provider: hindsight` and has its own
`hindsight/config.json`:

| Profile | Bank |
| --- | --- |
| default | hermes-default |
| gw-developer | hermes-gw-developer |
| gw-reviewer | hermes-gw-reviewer |
| local-ai | hermes-local-ai |
| the-dude | hermes-the-dude |

Banks separate normal provider reads and writes. They are not an authentication
boundary: clients with access to this server can select another bank.
When adding a profile, give it a `hindsight/config.json` with a unique bank and
enable the provider in its `config.yaml`. The startup hook discovers those configs.

Role defaults configure the LLM model, context window, timeout, multilingual
embedding/reranker models and plugin revision. Ollama uses CPU inference by
default; latency and RAM usage depend on the selected model and host. Choose a
larger model or configure GPU access if needed. The Hermes chat model settings
remain independent of the memory-processing model.

Persistent data under the deployment directory:

- `hindsight/data`: embedded PostgreSQL, included in borgmatic backups.
- `hindsight/cache`: downloaded embedding/reranking models, regenerated if lost.
- `ollama`: downloaded LLM models, regenerated if lost.
- `app`: Hermes profile configs, plugins and dependency state.

Borgmatic stops only Hindsight while backing up its PostgreSQL files and starts
it again on success or failure. Memory is temporarily unavailable during backup.
Stop Hindsight before restoring its data directory, then start it again.

After provisioning, check services and a profile from the deployment directory:

```sh
docker compose ps --all
docker compose logs app hindsight ollama-model
docker compose exec --user 10000:10000 app hermes --profile the-dude memory status
```

Use the configured Hermes UID/GID if overridden. First startup can take several
minutes for downloads and dependency preparation. To check separation, save a
distinct fact in one profile, then search for it in another profile using the
Hindsight memory tools; it should only be found in the originating profile.
