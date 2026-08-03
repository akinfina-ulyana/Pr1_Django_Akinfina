import factory

from users.models import User


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ("email",)
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f"user{n}@test.test")
    role = User.Role.BUYER
    is_active = True
    is_email_verified = True

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        self.set_password(extracted or "Test1234!")
        if create:
            self.save(update_fields=["password"])
