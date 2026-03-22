import modal

app = modal.App("my-project")

image = modal.Image.debian_slim().pip_install(
    "numpy",
    "pandas"
)

@app.function(image=image)
def hello():
    return "Hello from Modal!"