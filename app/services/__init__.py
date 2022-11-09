from app.services.custom_errors import CustomError, BadRequest, UnProcessable, Conflict, NoContent, \
    Forbidden, InternalError, Unauthorized
from app.services.crud import CRUD
from app.services.utils import email_validation
from app.services.auth import AuthService, admin_user_authorizer
from app.services.user_module import adding_new_users, admin_list_all_users
from app.services.projects_service import create_project, list_projects, edit_project, single_project
from app.services.multimedia import multimedia_upload, generate_pre_signed_url_multimedia, delete_proj_multimedia, generate_session_url, add_presenters, remove_presenter, upload_user_profile_pic, delete_s3_object, resource_s3, create_cloudformation_stack, check_cloudformation_stack_status, get_stack_instances_state, pass_domain_to_nodejs
from app.services.event_service import create_an_event, edit_an_event, delete_an_event, event_details_for_edit, get_proj_event_recordings
from app.services.presenter import video_call_presenter_validation, update_presenter_network_info, event_presenter_live_data, get_event_presenter_details
from app.services.recorder import start_chime_screen_recording, stop_chime_screen_recording, start_studio_screen_recording
from app.services.studio import create_studio, edit_studio, list_studios, single_studio, add_members_to_session, create_studio_session, edit_studio_session, session_details_for_edit, delete_studio_session, studio_session_call_presenter_validation, crud_session_presenters, get_studio_session_recordings, edit_studio_storage, get_studio_storage_cred