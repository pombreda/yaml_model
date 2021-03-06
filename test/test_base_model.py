"""
Test the Model class
"""
import pytest
import yaml

from yaml_model import LoadOnAccess, Model, NoValueError, ValidationError


SLUG_ERR_MESSAGE = 'Slug can not be blank'


@pytest.mark.usefixtures("cleandir")
class TestModel(object):
    """
    Test the Model class
    """
    @pytest.mark.parametrize('slugs', [
        ('testslug',),  # single
        ('myslug', 'myother', 'some'),  # multiple at a time
        ('with spaces',),  # space in slug
        ('Σ',),  # unicode slug
    ])
    def test_model_basic(self, cleandir, slugs):
        """
        Basic test of new model creation, load
        """
        class Test(Model):  # pylint:disable=missing-docstring
            slug = None
            test_field = LoadOnAccess()

            def __init__(self, slug):
                super(Test, self).__init__()
                self.slug = slug

        for slug in slugs:
            test_create = Test(slug)
            test_create.test_field = 'test value'

            assert not test_create.exists()
            test_create.save()
            assert test_create.exists()

            expected_file = cleandir.join('data', 'tests', '%s.yaml' % slug)
            assert expected_file.check(), "File exists"

            data = yaml.load(expected_file.open())
            assert data == {'test_field': 'test value'}

            test_load = Test(slug)
            assert test_load.exists()
            assert test_load.test_field == 'test value'

    def test_no_slug(self):
        """
        No override of slug causes exception
        """
        class Test(Model):  # pylint:disable=missing-docstring
            # pylint:disable=abstract-method
            pass

        test = Test()

        with pytest.raises(NotImplementedError):
            test.save()

    @pytest.mark.parametrize('slug_val', [None, ''])
    def test_blank_slug(self, slug_val):
        """
        Test that blank slugs raise ValidationError
        """
        class Test(Model):  # pylint:disable=missing-docstring
            slug = None

            def __init__(self, slug):
                super(Test, self).__init__()
                self.slug = slug

        with pytest.raises(ValidationError):
            Test(slug_val).save()

    @pytest.mark.parametrize('fields,has_test_field,has_other_field', [
        ({'test_field': 'test value'}, True, False),
        ({'test_field': None}, True, False),
        ({'other_field': 'test value'}, False, True),
        ({'test_field': 'test value', 'other_field': 'other'}, True, True),
        ({}, False, False),
    ])
    def test_has_value(self, fields, has_test_field, has_other_field):
        """
        Test the has_value function
        """
        class Test(Model):  # pylint:disable=missing-docstring
            slug = 'test'
            test_field = LoadOnAccess()
            other_field = LoadOnAccess()

        test = Test()
        for prop, val in fields.items():
            setattr(test, prop, val)

        assert test.has_value('test_field') == has_test_field
        assert test.has_value('other_field') == has_other_field

    def test_no_value(self):
        """
        Raises NoValueError when no value is given, no generater, and no
        default exists
        """
        pytest.skip("Requires fix")  # TODO don't skip this!

        class Test(Model):  # pylint:disable=missing-docstring
            slug = 'test'
            test_field = LoadOnAccess()

        test = Test()
        with pytest.raises(NoValueError):
            test.save()

    @pytest.mark.parametrize('parent_errors,child_errors,all_errors', [
        ('err', 'ex', {'err', 'ex', SLUG_ERR_MESSAGE}),
        (('err', 'err2'), 'ex', {'err', 'err2', 'ex', SLUG_ERR_MESSAGE}),
        ('err', ('ex', 'ex2'), {'err', 'ex', 'ex2', SLUG_ERR_MESSAGE}),
        (
            ('err', 'err2'), ('ex', 'ex2'),
            {'err', 'err2', 'ex', 'ex2', SLUG_ERR_MESSAGE}
        ),
        (None, 'ex', {'ex', SLUG_ERR_MESSAGE}),
        ('err', None, {'err', SLUG_ERR_MESSAGE}),
        (None, None, {SLUG_ERR_MESSAGE}),
    ])
    def test_parent_validation(self, parent_errors, child_errors, all_errors):
        """
        Test the parent_validation context manager to make sure it combines
        errors from all levels
        """
        class TestParent(Model):
            """
            Parent model, whose validation errors should bubble up
            """
            slug = None

            def validate(self):
                with self.parent_validation(TestParent):
                    if parent_errors:
                        raise ValidationError(parent_errors)

        class TestChild(TestParent):
            """
            Child model that validate will be called on
            """

            def validate(self):
                with self.parent_validation(TestChild):
                    if child_errors:
                        raise ValidationError(child_errors)

        test = TestChild()
        with pytest.raises(ValidationError):
            try:
                test.validate()
            except ValidationError as ex:
                assert set(ex.messages) == set(all_errors)
                raise

    @pytest.mark.parametrize('dirty', [True, False])
    def test_from_dict_dirty_flag(self, dirty):
        """
        Tests the from_dict method to make sure it properly applies properties
        and marks them as dirty, or cleanwho
        """
        class Test(Model):  # pylint:disable=missing-docstring
            slug = 'test'
            field1 = LoadOnAccess()
            field2 = LoadOnAccess()

        test = Test()
        test.from_dict({'field1': 'testfield1',
                        'field2': 'testfield2'}, dirty=dirty)
        assert test.field1 == 'testfield1'
        assert test.field2 == 'testfield2'
        assert test.is_dirty('field1') == dirty
        assert test.is_dirty('field2') == dirty

    def test_from_dict_missing(self):
        """
        Tests the from_dict method with only some model data
        """
        class Test(Model):  # pylint:disable=missing-docstring
            slug = 'test'
            field1 = LoadOnAccess()
            field2 = LoadOnAccess()

        test = Test()
        test.from_dict({'field1': 'testfield1'})
        assert test.field1 == 'testfield1'

        with pytest.raises(NoValueError):
            assert test.field2 == 'testfield2'

    def test_from_dict_extra(self):
        """
        Tests the from_dict method with extra data in the dict
        """
        class Test(Model):  # pylint:disable=missing-docstring
            slug = 'test'
            field1 = LoadOnAccess()

        test = Test()
        test.from_dict({'field1': 'testfield1', 'field2': 'testfield2'})
        assert test.field1 == 'testfield1'

    def test_as_dict(self):
        """
        Tests the as_dict method to make sure data is correctly "serialized"
        """
        class Test(Model):  # pylint:disable=missing-docstring
            slug = 'test'
            field1 = LoadOnAccess()
            field2 = LoadOnAccess()

        test = Test()
        test.field1 = 'testfield1'
        test.field2 = 'testfield2'
        assert test.as_dict() == {'field1': 'testfield1',
                                  'field2': 'testfield2'}

    @pytest.mark.parametrize('recheck_all', [True, False])
    @pytest.mark.parametrize('empty_mutable', [{}, []])
    def test_dirty_mutable(self, empty_mutable, recheck_all):
        """
        Change a mutable in place and make sure that object dirty checks still
        work
        """
        class Test(Model):  # pylint:disable=missing-docstring
            slug = 'test'
            mutable = LoadOnAccess()

        # Update the param will make it not empty any more in next tests :|
        empty_mutable = empty_mutable.copy()

        test = Test()
        test.mutable = empty_mutable
        test.save()

        assert not test.is_dirty('mutable'), (
            "Data is not dirty when just saved")

        if hasattr(empty_mutable, 'append'):
            empty_mutable.append('test')
        else:
            empty_mutable['test'] = 'test'

        if recheck_all:
            # Check `RuntimeError: dictionary changed size during iteration`
            test.recheck_dirty()

        assert test.is_dirty('mutable', recheck=not recheck_all)

    @pytest.mark.parametrize('empty_mutable,expected', [
        ({}, {'test': 'test'}),
        ([], ['test']),
    ])
    def test_load_with_dirty_mutable(self, empty_mutable, expected):
        """
        Test loading over dirty mutable values to make sure that it's not
        erased
        """
        class Test(Model):  # pylint:disable=missing-docstring
            slug = 'test'
            mutable = LoadOnAccess()

        test = Test()
        test.mutable = empty_mutable
        test.save()

        if hasattr(empty_mutable, 'append'):
            empty_mutable.append('test')

        else:
            empty_mutable['test'] = 'test'

        test.load(recheck_dirty=True)
        assert test.mutable == expected

    def test_from_dict_mutable_clean(self):
        """
        Test the from_dict method resets hashes for mutable, lazy values
        """
        class Test(Model):  # pylint:disable=missing-docstring
            slug = 'test'
            mutable = LoadOnAccess()

        test = Test()
        test.mutable = []
        test.save()

        assert not test.is_dirty('mutable')

        test.from_dict({'mutable': [True]}, dirty=False)
        assert not test.is_dirty('mutable')

    @pytest.mark.parametrize('slugs', [
        ('testslug',),
        ('myslug', 'myother', 'some'),
        ('with spaces', 'some more spaces'),
        ('Σ', 'œø'),
    ])
    def test_all_data_dir(self, cleandir, slugs):
        """
        Test the Model.all function, with a set data_dir
        """
        created_slugs = []

        class Test(Model):  # pylint:disable=missing-docstring
            slug = None

            def __init__(self, slug):
                created_slugs.append(slug)
                super(Test, self).__init__()

        files = [
            cleandir.join('%s.yaml' % slug)
            for slug in slugs
        ]
        for filename in files:
            filename.ensure()

        tuple(Test.all(data_dir=cleandir))
        assert set(created_slugs) == set(slugs)

    @pytest.mark.parametrize('slugs', [
        ('myslug', 'myother', 'some'),
    ])
    @pytest.mark.parametrize('args', [
        ('arg', 'kwarg'),
        (None, None),
        ({}, []),
    ])
    def test_all_pass_args(self, cleandir, slugs, args):
        """
        Test the Model.all function, with additional args to __init__
        """
        created_slugs = []

        class Test(Model):  # pylint:disable=missing-docstring
            slug = None

            def __init__(self, slug, arg_a, kwarg_a=None):
                created_slugs.append(slug)
                assert arg_a == args[0]
                assert kwarg_a == args[1]
                super(Test, self).__init__()

        data_dir = cleandir.join('data', 'tests')
        files = [
            data_dir.join('%s.yaml' % slug)
            for slug in slugs
        ]
        for filename in files:
            filename.ensure()

        tuple(Test.all(new_args=(args[0],),
                       new_kwargs={'kwarg_a': args[1]}
                       ))
        assert set(created_slugs) == set(slugs)

    @pytest.mark.parametrize('slug', [
        'myslug', 'with spaces', 'Σ',
    ])
    @pytest.mark.parametrize('good_link_names', [
        ('mysluglink',),
        ('mysluglink', 'morelink'),
        ('with spaces link', 'more link'),
        ('Σlink', 'œølink'),
    ])
    @pytest.mark.parametrize('fake_link_names', [
        (),
        ('bogus', 'Σœø'),
    ])
    def test_all_dereference(self,
                             cleandir,
                             slug,
                             good_link_names,
                             fake_link_names):
        """
        Test the Model.all function, with a set data_dir
        """
        created_slugs = []

        class Test(Model):  # pylint:disable=missing-docstring
            slug = None

            def __init__(self, slug):
                created_slugs.append(slug)
                super(Test, self).__init__()

        root_file = cleandir.join('data', 'tests', '%s.yaml' % slug)
        root_file.ensure()
        fake_file = cleandir.join('fake.yaml')
        fake_file.ensure()

        links_dir = cleandir.join('links')
        links_dir.ensure_dir()

        link_loop_data = (
            (good_link_names, root_file),
            (fake_link_names, fake_file),
        )
        for link_names, to_file in link_loop_data:
            links = [
                links_dir.join('%s.yaml' % name)
                for name in link_names
            ]
            for filename in links:
                filename.mksymlinkto(to_file)

        tuple(Test.all(data_dir=links_dir,
                       dereference=True,
                       skip_non_model=True))
        assert created_slugs == [slug] * len(good_link_names)
