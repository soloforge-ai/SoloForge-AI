class ReverseDependencyBuilder:

    def build(self, inventory):

        path_index = {
            item.path.replace("\\", "/"): item
            for item in inventory
        }

        for item in inventory:

            for dependency in item.dependencies:

                dependency = dependency.replace("\\", "/")

                if dependency in path_index:

                    path_index[
                        dependency
                    ].used_by.append(
                        item.path.replace("\\", "/")
                    )

        return inventory