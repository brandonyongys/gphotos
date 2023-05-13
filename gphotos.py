import pickle
import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

class GooglePhotosApi:
    def __init__(self,
                 client_secret_file,
                 api_version = 'v1',
                 api_name = 'photoslibrary',
                 scopes = ['https://www.googleapis.com/auth/photoslibrary']):
        '''
        Args:
            client_secret_file: string, location where the requested credentials are saved
            api_version: string, the version of the service
            api_name: string, name of the api e.g."docs","photoslibrary",...
            api_version: version of the api
        '''
        self.client_secret_file = client_secret_file
        self.api_version = api_version
        self.api_name = api_name
        self.scopes = scopes
        self.cred_pickle_file = f'./credentials/token_{self.api_name}_{self.api_version}.pickle'
        self.cred = None
        self.service = None

    def run_local_server(self):
        """
        Function:   Check for existing credential pickle.
                    Load the credential token
        """

        # is checking if there is already a pickle file with relevant credentials
        if os.path.exists(self.cred_pickle_file):
            with open(self.cred_pickle_file, 'rb') as token:
                self.cred = pickle.load(token)

        # if there is no pickle file with stored credentials, create one using google_auth_oauthlib.flow
        if not self.cred or not self.cred.valid:
            if self.cred and self.cred.expired and self.cred.refresh_token:
                self.cred.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.client_secret_file, self.scopes)
                self.cred = flow.run_local_server()

            with open(self.cred_pickle_file, 'wb') as token:
                pickle.dump(self.cred, token)
        
        return self.cred

    def delete_pickle_file(self):
        """
        Function:   Delete the credentials pickle file
        """
        os.remove(self.cred_pickle_file)
        print("Deleted the credential pickle file.")
