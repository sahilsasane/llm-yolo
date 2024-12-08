import pandas as pd
import os
from typing import Optional, List, Dict, Union
import logging


class DataProcessor:
    """
    A class for processing and cleaning data files.
    Handles CSV and Excel files with various cleaning operations.
    """

    def __init__(self, threshold: float = 0.5):
        """
        Initialize the DataProcessor.

        Args:
            threshold (float): Minimum percentage of non-NA values required in a row (0-1)
        """
        self.threshold = threshold
        self.logger = logging.getLogger(__name__)
        self._supported_extensions = {".csv", ".xls", ".xlsx"}

    def clean_and_process_file(
        self,
        file_path: str,
        output_path: str,
        encoding: str = "utf-8",
        delimiter: str = ",",
    ) -> Optional[pd.DataFrame]:
        """
        Clean and process a data file.

        Args:
            file_path (str): Path to input file
            output_path (str): Path to save cleaned file
            encoding (str): File encoding
            delimiter (str): CSV delimiter

        Returns:
            Optional[pd.DataFrame]: Cleaned DataFrame or None if processing fails
        """
        try:
            # Load and validate file
            df = self._load_file(file_path, encoding, delimiter)
            if df is None:
                return None

            # Apply cleaning operations
            df = self._clean_dataframe(df)

            # Save processed file
            self._save_file(df, output_path, file_path)

            self.logger.info(f"Cleaning complete. Cleaned file saved to: {output_path}")
            return df

        except Exception as e:
            self.logger.error(f"Error during cleaning: {str(e)}")
            return None

    def _load_file(
        self, file_path: str, encoding: str, delimiter: str
    ) -> Optional[pd.DataFrame]:
        """Load data file based on extension."""
        file_extension = os.path.splitext(file_path)[1].lower()

        if file_extension not in self._supported_extensions:
            self.logger.error(
                "Unsupported file format. Please provide a CSV or Excel file."
            )
            return None

        try:
            if file_extension == ".csv":
                return pd.read_csv(
                    file_path,
                    encoding=encoding,
                    delimiter=delimiter,
                    on_bad_lines="skip",
                    engine="python",
                )
            else:  # Excel files
                return pd.read_excel(file_path, engine="openpyxl")

        except Exception as e:
            self.logger.error(f"Error loading file: {str(e)}")
            return None

    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply all cleaning operations to DataFrame."""
        df = self._standardize_columns(df)
        df = self._remove_duplicates(df)
        df = self._handle_missing_values(df)
        df = self._convert_numeric_columns(df)
        df = self._remove_invalid_rows(df)
        return df

    def _standardize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize column names."""
        df.columns = (
            df.columns.str.strip()
            .str.lower()
            .str.replace(" ", "_")
            .str.replace(r"[^a-zA-Z0-9_]", "", regex=True)
        )
        return df

    def _remove_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove duplicate rows."""
        return df.drop_duplicates()

    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle missing values in DataFrame."""
        # Drop rows with too many missing values
        df = df.dropna(thresh=int(self.threshold * len(df.columns)))

        # Fill missing values in numeric columns
        numeric_cols = df.select_dtypes(include=["float64", "int64"]).columns
        if not numeric_cols.empty:
            df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].mean())

        return df

    def _convert_numeric_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert object columns to numeric where possible."""
        for col in df.select_dtypes(include=["object"]).columns:
            first_value = df[col].iloc[0] if not df[col].empty else None
            if isinstance(first_value, str) and first_value.isnumeric():
                df[col] = pd.to_numeric(df[col], errors="coerce")

                # Fill new NaN values after conversion
                if pd.api.types.is_numeric_dtype(df[col]):
                    df[col] = df[col].fillna(df[col].mean())

        return df

    def _remove_invalid_rows(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove rows with invalid or corrupted data."""
        return df[df.applymap(lambda x: isinstance(x, (int, float, str))).all(axis=1)]

    def _save_file(
        self, df: pd.DataFrame, output_path: str, original_path: str
    ) -> None:
        """Save processed DataFrame to file."""
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            if output_path.endswith(".csv"):
                df.to_csv(output_path, index=False, encoding="utf-8")
            elif output_path.endswith((".xls", ".xlsx")):
                df.to_excel(output_path, index=False, engine="openpyxl")

        except Exception as e:
            self.logger.error(f"Error saving file: {str(e)}")
            raise
