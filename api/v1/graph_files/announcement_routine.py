import configparser
from configparser import SectionProxy
import re
import numpy as np

from .institute import Institute
from .students import Students
from . import helpers
from .config import create_graph_service_client,create_cosmos_service_client



from azure.identity.aio import ClientSecretCredential
from kiota_authentication_azure.azure_identity_authentication_provider import (
    AzureIdentityAuthenticationProvider
)
from msgraph import GraphRequestAdapter, GraphServiceClient
from msgraph.generated.applications.get_available_extension_properties import \
    get_available_extension_properties_post_request_body
from msgraph.generated.groups.groups_request_builder import GroupsRequestBuilder
from msgraph.generated.models.group import Group
from msgraph.generated.models.item_body import ItemBody
from msgraph.generated.models.message import Message
from msgraph.generated.models.body_type import BodyType
from msgraph.generated.models.email_address import EmailAddress
from msgraph.generated.models.file_attachment import FileAttachment
from msgraph.generated.models.recipient import Recipient
from msgraph.generated.models.reference_create import ReferenceCreate
from msgraph.generated.users.users_request_builder import UsersRequestBuilder
from azure.cosmos import CosmosClient, DatabaseProxy
from msgraph.generated.models.user import User
from msgraph.generated.users.users_request_builder import UsersRequestBuilder
from msgraph.generated.users.item.send_mail.send_mail_request_builder import SendMailRequestBuilder
from msgraph.generated.users.item.messages.item.message_item_request_builder import MessageItemRequestBuilder
from msgraph.generated.users.item.send_mail.send_mail_post_request_body import SendMailPostRequestBody
import base64
from base64 import urlsafe_b64decode, urlsafe_b64encode

config = configparser.ConfigParser()
config.read(['config.cfg', 'config.dev.cfg'])
azure_settings = config['azure']

students_instance = Students(azure_settings)
institute_instance = Institute(azure_settings)

class AnnouncementRoutine:
    settings: SectionProxy
    client_credential: ClientSecretCredential
    app_client: GraphServiceClient
    client:CosmosClient

    def __init__(self, config: SectionProxy): 
        self.settings = config
        self.client = create_cosmos_service_client(config)
        self.db = self.client.get_database_client('courses_manipal')
        self.container = self.db.get_container_client('courses_manipal')
        self.app_client = create_graph_service_client(config)


    async def make_announcement_admin(self,user_id:str,subject:str,announcement_message:str,file_attachments:list,target_group_mails:list):
        request_body = SendMailPostRequestBody(
            message = Message(
                subject = subject,
                body = ItemBody(
                    content_type = BodyType.Text,
                    content = announcement_message,
                ),
                to_recipients = [
                    Recipient(
                        email_address=EmailAddress(
                            address=target_group_mail,
                        )
                    ) for target_group_mail in target_group_mails
                ],
                attachments = [
                    FileAttachment(
                        odata_type = "#microsoft.graph.fileAttachment",
                        name = file_attachment.filename,
                        content_type = file_attachment.content_type,
                        content_bytes = await file_attachment.read(),
                    ) for file_attachment in file_attachments
                ],
            ),
        )
        await self.app_client.users.by_user_id(user_id).send_mail.post(request_body)

    async def get_all_announcements(self, user_id):
        query_params = MessageItemRequestBuilder.MessageItemRequestBuilderGetQueryParameters(
		    select = ["subject","from","body"],
        )
        request_configuration = MessageItemRequestBuilder.MessageItemRequestBuilderGetRequestConfiguration(
            query_parameters = query_params,
        )
        request_configuration.headers.add("Prefer", "outlook.body-content-type=\"text\"")

        return await self.app_client.users.by_user_id(user_id).messages.get(request_configuration = request_configuration)

    async def make_announcement_dev(self,user_id:str,subject:str,announcement_message:str,file_attachments:list,target_group_mails:list):
        message_request_body = Message(
                subject = subject,
                body = ItemBody(
                    content_type = BodyType.Text,
                    content = announcement_message,
                ),
                to_recipients = [
                    Recipient(
                        email_address=EmailAddress(
                            address=target_group_mail,
                        )
                    ) for target_group_mail in target_group_mails
                ]
        )
        message_response = await self.app_client.users.by_user_id(user_id).messages.post(message_request_body)
        message_id = message_response.id
        announcement_properties = {
            "date_received": message_response.received_date_time,
            "announcement_id": message_response.id,
            "to_recipients": message_response.to_recipients
            }
            
        message_date_time = message_response.received_date_time

        for file_attachment in file_attachments:
            attachment_request_body = FileAttachment(
                        odata_type = "#microsoft.graph.fileAttachment",
                        name = file_attachment['file_name'],
                        content_type = file_attachment["content_type"],
                        content_bytes = base64.urlsafe_b64decode(file_attachment["content_bytes"]),
                    )
            attachment_response = await self.app_client.users.by_user_id(user_id).messages.by_message_id(message_id).post(attachment_request_body)
        await self.app_client.users.by_user_id(user_id).messages.by_message_id(message_id).send()
        return announcement_properties


        

        
