from fastapi import FastAPI

app = FastAPI(
    title="File2MD",
    description="Universal File-to-Markdown Converter",
    version="1.0.0",
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Welcome to File2MD API. Visit /docs for OpenAPI specifications."}