def select_sources(playlists: list[dict]) -> list[str]:
    """
    Display an interactive numbered menu and return a list of source identifiers.
    Each source is either 'liked' or a Spotify playlist id.
    """
    print("\nSelect sources to download:")
    print("  0) Liked Songs")
    for i, pl in enumerate(playlists, start=1):
        print(f"  {i}) {pl['name']} ({pl['track_count']} tracks) — {pl['owner']}")
    print("\nEnter numbers separated by commas, or 'all' for everything:")

    while True:
        raw = input("> ").strip().lower()
        if raw == "all":
            return ["liked"] + [pl["id"] for pl in playlists]

        try:
            indices = [int(x.strip()) for x in raw.split(",") if x.strip()]
        except ValueError:
            print("Invalid input. Enter numbers separated by commas or 'all'.")
            continue

        if not indices:
            print("No selection made. Please enter at least one number.")
            continue

        invalid = [i for i in indices if i < 0 or i > len(playlists)]
        if invalid:
            print(f"Invalid indices: {invalid}. Valid range is 0–{len(playlists)}.")
            continue

        sources = []
        for i in indices:
            if i == 0:
                sources.append("liked")
            else:
                sources.append(playlists[i - 1]["id"])
        return sources
