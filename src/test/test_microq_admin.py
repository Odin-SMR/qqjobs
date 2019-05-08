import pytest
from subprocess import check_output, CalledProcessError


@pytest.mark.slow
def test_can_get_main_help(microq_admin):
    out = check_output(['./microq_admin.sh', '--help'])
    assert 'MicroQ Admin' in out


@pytest.mark.slow
@pytest.mark.parametrize("service,helptitle", (
    ('delete-claims', 'Release Claim'),
    ('qsmrjobs', 'Add qsmr jobs to the microq job service'),
    ('qsmrprojects', 'Add a processing project to the microq job service'),
))
def test_can_get_service_help(service, helptitle, microq_admin):
    out = check_output(['./microq_admin.sh', service, '--help'])
    assert helptitle in out


@pytest.mark.slow
def test_invalid_service(microq_admin):
    with pytest.raises(CalledProcessError):
        check_output(['./microq_admin.sh', 'xxx'])
