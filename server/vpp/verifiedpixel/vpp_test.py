from flask import current_app as app
from eve.utils import config, ParsedRequest
import json
import ntpath
import imghdr

from superdesk import get_resource_service
from superdesk.media.renditions import generate_renditions
from superdesk.upload import url_for_media
from superdesk.tests import setup as superdesk_setup
from app import get_app


def setup(context, app_factory=None):
    if not app_factory:
        app_factory = get_app
    return superdesk_setup(context=context, app_factory=app_factory)


class VPPTestCase:

    def upload_fixture_image(
        self, fixture_image_path,
        verification_stats_path, verification_result_path, headline='test'
    ):
        with self.app.app_context():
            with open(fixture_image_path, mode='rb') as f:
                file_name = ntpath.basename(fixture_image_path)
                file_type = 'image'
                content_type = '%s/%s' % (file_type, imghdr.what(f))
                file_id = app.media.put(
                    f, filename=file_name,
                    content_type=content_type,
                    resource=get_resource_service('ingest').datasource,
                    metadata={}
                )
                inserted = [file_id]
                renditions = generate_renditions(
                    f, file_id, inserted, file_type, content_type,
                    rendition_config=config.RENDITIONS['picture'],
                    url_for_media=url_for_media
                )
            data = [{
                'headline': headline,
                'slugline': 'rebuild',
                'renditions': renditions,
                'type': 'picture'
            }]
            image_id = get_resource_service('ingest').post(data)
        with open(verification_result_path, 'r') as f:
            self.expected_verification_results.append(json.load(f))
        with open(verification_stats_path, 'r') as f:
            self.expected_verification_stats.append(json.load(f))
        return image_id

    @classmethod
    def purge_index(cls, resource_name):
        """
        workaround for gridfs index problem,
        """
        with cls.app.app_context():
            connection = cls.app.data.mongo.pymongo(
                resource=resource_name
            ).cx
            connection._purge_index(
                cls.app.config['MONGO_DBNAME']
            )

    def assertVerificationResult(self, result, stats_references, verification_references):
        verification_results = result['results']
        verification_stats = result['stats']
        if not isinstance(verification_results, dict):
            verification_results = list(get_resource_service('verification_results').get(
                req=ParsedRequest(), lookup={'_id': verification_results}
            ))[0]
            # _id = verification_results['_id']
            for field in ['_id', '_etag', '_created', '_updated']:
                del verification_results[field]
            # with open(str(_id), 'w') as f:
                # json.dump(verification_results, f)
        self.assertEqual(verification_stats, stats_references)
        self.assertEqual(verification_results, verification_references)
