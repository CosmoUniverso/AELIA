from runtime.organism_runtime import OrganismRuntime
from ui.renderer import Renderer


def main() -> None:
    runtime = OrganismRuntime()
    renderer = Renderer(runtime)
    renderer.run()


if __name__ == '__main__':
    main()
