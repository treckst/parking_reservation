# Build the graph image first; reuse its installed application dependencies.
FROM parking-graph:phase01
ENTRYPOINT []
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app/src
# Copy source/static assets explicitly; never copy credentials or runtime data.
COPY src ./src
EXPOSE 8080
CMD ["uvicorn", "parking.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8080"]
