from collections import OrderedDict

from drf_yasg.generators import OpenAPISchemaGenerator
from drf_yasg.inspectors import SwaggerAutoSchema

# OpenAPI 2 だと、write_onlyが正しく反映されない問題があるため、このスキーマを間に使う
# 参照：https://github.com/axnsan12/drf-yasg/issues/70#issuecomment-485050813
from drf_yasg.utils import no_body

nested_keys = ["images", "members"]


class BlankMeta:
    pass


class ReadOnly:
    def get_fields(self):
        new_fields = OrderedDict()
        for fieldName, field in super().get_fields().items():
            if not field.write_only:
                new_fields[fieldName] = field

        return new_fields


class NestedCreateReadOnly:
    def get_fields(self):
        new_fields = OrderedDict()
        for fieldName, field in super().get_fields().items():
            modified = False
            for key in nested_keys:
                if fieldName == key:
                    # key が消えた状態でキャッシュされている可能性があるので、その回避策
                    if key in field.child._declared_fields:
                        field.child._declared_fields.pop(key)

                    fields_tuple = list(field.child.Meta.fields)
                    update_fields = [f for f in fields_tuple if f != key]
                    field.child.Meta.fields = tuple(update_fields)
                    new_fields[fieldName] = field
                    modified = True
                    break
            if modified:
                continue

            if not field.write_only:
                new_fields[fieldName] = field
        return new_fields


class WriteOnly:
    def get_fields(self):
        new_fields = OrderedDict()
        for fieldName, field in super().get_fields().items():
            if not field.read_only:
                new_fields[fieldName] = field
        return new_fields


class NestedCreateWriteOnly:
    def get_fields(self):
        new_fields = OrderedDict()
        for fieldName, field in super().get_fields().items():
            modified = False
            for key in nested_keys:
                if fieldName == key:
                    # nested_list が消えた状態でキャッシュされている可能性があるので、その回避策
                    if key in field.child._declared_fields:
                        field.child._declared_fields.pop(key)

                    fields_tuple = list(field.child.Meta.fields)
                    update_fields = [f for f in fields_tuple if f != key]
                    field.child.Meta.fields = tuple(update_fields)
                    new_fields[fieldName] = field
                    modified = True
                    break
            if modified:
                continue

            if not field.read_only:
                new_fields[fieldName] = field
        return new_fields


class ReadWriteAutoSchema(SwaggerAutoSchema):
    def get_view_serializer(self):
        return self._convert_serializer(NestedCreateWriteOnly)

    def get_default_response_serializer(self):
        body_override = self._get_request_body_override()
        if body_override and body_override is not no_body:
            return body_override

        return self._convert_serializer(NestedCreateReadOnly)

    def _convert_serializer(self, new_class):
        serializer = super().get_view_serializer()
        if not serializer:
            return serializer

        class CustomSerializer(new_class, serializer.__class__):
            class Meta(getattr(serializer.__class__, "Meta", BlankMeta)):
                ref_name = new_class.__name__ + serializer.__class__.__name__

        new_serializer = CustomSerializer(data=serializer.data)
        return new_serializer


class BothHttpAndHttpsSchemaGenerator(OpenAPISchemaGenerator):
    def get_schema(self, request=None, public=False):
        schema = super().get_schema(request, public)
        schema.schemes = ["http", "https"]
        return schema
