FROM nousresearch/hermes-agent:v0.23.1

# renovate: git-refs=https://github.com/Acrazt05/hermes_github_app_plugin.git ref=main
ARG HERMES_GITHUB_APP_REV=4e9b4e24f751165253d7e4d4e81a4ec487515737

RUN apt-get update && \
    apt-get install --yes --no-install-recommends \
            gh \
            python3-venv && \
    rm -rf /var/lib/apt/lists/* && \
    \
    git clone --quiet https://github.com/Acrazt05/hermes_github_app_plugin.git /opt/hermes/plugins/github-app && \
    git -C /opt/hermes/plugins/github-app checkout --quiet "${HERMES_GITHUB_APP_REV}" && \
    /usr/bin/python3 -m venv /opt/github-app && \
    /opt/github-app/bin/pip install --no-cache-dir /opt/hermes/plugins/github-app && \
    # Webhook scripts run with Hermes's interpreter, separate from gh-app.
    /opt/github-app/bin/pip --python /opt/hermes/.venv/bin/python install --no-cache-dir PyYAML && \
    /opt/hermes/.venv/bin/python -c "import yaml" && \
    /opt/github-app/bin/gh-app --help && \
    /opt/github-app/bin/git-app --help

COPY __init__.py /opt/hermes/plugins/github-app/__init__.py

ENV PATH="/opt/github-app/bin:${PATH}"
