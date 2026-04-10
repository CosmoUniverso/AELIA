from runtime.organism_runtime import OrganismRuntime


def main() -> None:
    runtime = OrganismRuntime()
    runtime.run_headless(max_ticks=5000, verbose_every=25)


if __name__ == '__main__':
    main()
