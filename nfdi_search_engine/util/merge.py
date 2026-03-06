def merge_objects(object_list: list, mapping_preference: dict):
    """
    This function revieces a list of objects defined in objects.py, and returns a new object with the merged values of the objects in object_list.

    :param object_list: The list of objects to merge
    :type object_list: list
    :param mapping_preference: The dict containing the preference order
    :type mapping_preference: dict
    """

    # the new object we create will have the type of the object in object_list which is furthest down in the inheritance hierarchy
    # => we search for the obj with the longest __mro__
    target_obj = max(object_list, key=lambda x: len(type(x).__mro__))
    target_cls = type(target_obj)
    merged_object = target_cls()

    # this function returns the index of the source in the preference list for the field
    # it returns float('inf') if the source is not in the preference list
    def get_preference_index(obj, field_name):
        # get the name of the source of the object
        source_list = getattr(obj, "source", None)
        source = source_list[0] if source_list else None
        source_name = getattr(source, "name", None) if source else None

        # get the preference order for the field
        pref_list: list = mapping_preference.get(
            field_name, mapping_preference.get("__default__", [])
        )

        return (
            pref_list.index(source_name)
            if source_name in pref_list else float("inf")
        )

    # collect all sources that will be used in the merged object
    sources = set()

    # iterate through the sorted objects and choose the first non-empty value for each field in the merged object
    for field in type(merged_object).model_fields.keys():
        # sort the objects by the current field
        # if the field is not found, the objects are sorted with the __default__ list
        sorted_objects = sorted(
            object_list, key=lambda obj: get_preference_index(obj, field)
        )

        # iterate through the sorted objects until one of them contains a non-empty value for the field
        for obj in sorted_objects:
            val = getattr(obj, field, None)

            # check if the value is empty or a placeholder
            if val not in (None, "",[],{},):
                setattr(merged_object, field, val)

                # add all sources to the merged object
                source_list = set(getattr(obj, "source", []))
                sources.update(source_list)

                break

    # add the sources to the merged object
    merged_object.source = list(sources)

    return merged_object
