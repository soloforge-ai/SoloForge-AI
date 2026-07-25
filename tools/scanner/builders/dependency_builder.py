import posixpath


class DependencyBuilder:

    def build(
        self,
        inventory,
    ):

        # path -> InventoryItem
        path_index = {}

        # filename -> [paths]
        filename_index = {}

        for item in inventory:

            path = item.path.replace("\\", "/")

            path_index[path] = item

            filename_index.setdefault(
                item.name,
                []
            ).append(path)

        for item in inventory:

            current_folder = posixpath.dirname(
                item.path.replace("\\", "/")
            )

            dependencies = []

            for imported in item.imports:

                imported = imported.replace("\\", "/")

                # -----------------------------
                # External packages
                # -----------------------------
                if imported.startswith("package:"):

                    # package:flutter/*
                    if imported.startswith("package:flutter/"):
                        continue

                    filename = posixpath.basename(imported)

                    dependencies.extend(
                        filename_index.get(
                            filename,
                            []
                        )
                    )

                    continue

                # -----------------------------
                # Relative imports
                # -----------------------------
                if imported.startswith("."):

                    resolved = posixpath.normpath(
                        posixpath.join(
                            current_folder,
                            imported,
                        )
                    )

                    if resolved in path_index:
                        dependencies.append(resolved)
                        continue

                # -----------------------------
                # Same folder imports
                # -----------------------------
                filename = posixpath.basename(imported)

                dependencies.extend(
                    filename_index.get(
                        filename,
                        []
                    )
                )

            item.dependencies = sorted(
                set(dependencies)
            )

        return inventory