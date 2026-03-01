import fsspec, posixpath
import streamlit as st
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
from utils.data_handler import DataHandler


def _ch_now():
    """Returns current Swiss time as a timezone-naive pandas Timestamp, floored to seconds."""
    return pd.Timestamp(datetime.now(ZoneInfo('Europe/Zurich')).replace(tzinfo=None)).floor('s')


class DataManager:
    """
    A singleton class for managing application data persistence.

    Provides load and save operations for both application-wide and user-specific
    data files. Uses fsspec for filesystem abstraction (local or WebDAV).

    Session state is NOT managed by this class — callers are responsible for
    reading from and writing to st.session_state explicitly.

    Attributes:
        fs (fsspec.AbstractFileSystem): The filesystem interface
        fs_root_folder (str): Root directory for all file operations
    """

    def __new__(cls, *args, **kwargs):
        """Singleton: returns existing instance from session state if available."""
        if 'data_manager' in st.session_state:
            return st.session_state.data_manager
        instance = super(DataManager, cls).__new__(cls)
        st.session_state.data_manager = instance
        return instance

    def __init__(self, fs_protocol='file', fs_root_folder='app_data'):
        """
        Initialize the data manager with filesystem configuration.

        Args:
            fs_protocol (str): Protocol for filesystem operations ('file' or 'webdav').
            fs_root_folder (str): Base directory path for all file operations.
        """
        if hasattr(self, 'fs'):
            return
        self.fs_root_folder = fs_root_folder
        self.fs = self._init_filesystem(fs_protocol)

    def info(self):
        """Returns a string with information about the DataManager's internal state."""
        return (
            f"DataManager Information:\n"
            f"  Filesystem Type: {type(self.fs).__name__}\n"
            f"  Root Folder: {self.fs_root_folder}\n"
        )

    @staticmethod
    def _init_filesystem(protocol: str):
        """
        Creates and configures an fsspec filesystem instance.

        Args:
            protocol (str): The filesystem protocol ('webdav' or 'file').

        Returns:
            fsspec.AbstractFileSystem: Configured filesystem instance.

        Raises:
            ValueError: If an unsupported protocol is specified.
        """
        if protocol == 'webdav':
            try:
                secrets = st.secrets['webdav']
            except (KeyError, FileNotFoundError):
                st.error("WebDAV-Konfiguration fehlt. Bitte überprüfen Sie die secrets.toml Datei.")
                st.stop()
            try:
                return fsspec.filesystem('webdav',
                                         base_url=secrets['base_url'],
                                         auth=(secrets['username'], secrets['password']))
            except Exception as e:
                st.error(f"Verbindung zu WebDAV fehlgeschlagen: {e}")
                st.stop()
        elif protocol == 'file':
            return fsspec.filesystem('file')
        else:
            raise ValueError(f"DataManager: Invalid filesystem protocol: {protocol}")

    def _get_data_handler(self, subfolder=None):
        """
        Creates a DataHandler instance for the specified subfolder.

        Args:
            subfolder (str, optional): Subfolder path relative to root folder.

        Returns:
            DataHandler: Configured for operations in the specified folder.
        """
        if subfolder is None:
            return DataHandler(self.fs, self.fs_root_folder)
        return DataHandler(self.fs, posixpath.join(self.fs_root_folder, subfolder))

    def load_app_data(self, file_name, initial_value=None, **load_args):
        """
        Load application-wide data from a file.

        Args:
            file_name (str): Name of the file to load.
            initial_value: Default value if the file doesn't exist.
            **load_args: Additional arguments passed to the file loader.

        Returns:
            The loaded data (DataFrame, dict, list, etc.).
        """
        dh = self._get_data_handler()
        return dh.load(file_name, initial_value, **load_args)

    def load_user_data(self, file_name, initial_value=None, **load_args):
        """
        Load user-specific data from the current user's data folder.

        Args:
            file_name (str): Name of the file to load.
            initial_value: Default value if the file doesn't exist.
            **load_args: Additional arguments passed to the file loader.

        Returns:
            The loaded data, or initial_value if no user is logged in.
        """
        username = st.session_state.get('username')
        if username is None:
            st.error(f"DataManager: No user logged in, cannot load '{file_name}'")
            return initial_value
        dh = self._get_data_handler('user_data_' + username)
        return dh.load(file_name, initial_value, **load_args)

    def save_app_data(self, data, file_name):
        """
        Save application-wide data to a file.

        Args:
            data: The data to save (DataFrame, dict, list, str, or bytes).
            file_name (str): Name of the file to save to.
        """
        dh = self._get_data_handler()
        dh.save(file_name, data)

    def save_user_data(self, data, file_name):
        """
        Save user-specific data to the current user's data folder.

        Args:
            data: The data to save (DataFrame, dict, list, str, or bytes).
            file_name (str): Name of the file to save to.
        """
        username = st.session_state.get('username')
        if username is None:
            st.error("DataManager: No user logged in, cannot save data")
            return
        dh = self._get_data_handler('user_data_' + username)
        dh.save(file_name, data)

    @staticmethod
    def append_record(data, record_dict):
        """
        Append a new record to a DataFrame or list and return the result.

        This is a pure function — it does not modify session state or save to
        storage. Use save_user_data() or save_app_data() to persist the result.

        A timestamp is automatically added if not present in record_dict.

        Args:
            data (pd.DataFrame or list): The existing data to append to.
            record_dict (dict): The new record to append.

        Returns:
            A new DataFrame or list with the record appended.

        Raises:
            ValueError: If record_dict is not a dict, or data is not a DataFrame/list.
        """
        if not isinstance(record_dict, dict):
            raise ValueError("DataManager: record_dict must be a dictionary")

        if 'timestamp' not in record_dict:
            record_dict = {**record_dict, 'timestamp': _ch_now()}

        if isinstance(data, pd.DataFrame):
            return pd.concat([data, pd.DataFrame([record_dict])], ignore_index=True)
        elif isinstance(data, list):
            return data + [record_dict]
        else:
            raise ValueError("DataManager: data must be a DataFrame or a list")
