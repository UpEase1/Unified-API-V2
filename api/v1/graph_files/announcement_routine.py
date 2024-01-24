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
from msgraph.generated.models.item_body import ItemBody
from msgraph.generated.models.message import Message
from msgraph.generated.models.body_type import BodyType
from msgraph.generated.models.email_address import EmailAddress
from msgraph.generated.models.file_attachment import FileAttachment
from msgraph.generated.models.recipient import Recipient
from msgraph.generated.users.item.messages.item.message_item_request_builder import MessageItemRequestBuilder
from msgraph.generated.users.item.send_mail.send_mail_post_request_body import SendMailPostRequestBody


config = configparser.ConfigParser()
config.read(['config.cfg', 'config.dev.cfg'])
azure_settings = config['azure']

students_instance = Students(azure_settings)
institute_instance = Institute(azure_settings)

class AnnouncementRoutine:
    settings: SectionProxy

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
                select = ["subject","body","bodyPreview","uniqueBody"],
        )

        request_configuration = MessageItemRequestBuilder.MessageItemRequestBuilderGetRequestConfiguration(
        query_parameters = query_params,
        )
        request_configuration.headers.add("Prefer", "outlook.body-content-type=\"text\"")

        messages = await self.app_client.users.by_user_id(user_id).messages.get(request_configuration = request_configuration)

        messages_list = messages.backing_store.get("value")

        final_messages_list = []

        for message in messages_list:
            # attachments = await self.app_client.users.by_user_id(user_id).messages.by_message_id(message.id).attachments.get()

            # final_attachments_list = []

            # for attachment in attachments.backing_store.get("value"):
            #     print(dir(attachment))
            #     final_attachments_list.append(attachment.content_bytes)

            final_messages_list.append({
                "subject": message.subject,
                "content": message.body.content,
                # "attachments": final_attachments_list
            })           
        
        return final_messages_list
    
    # todo Get attachment by id