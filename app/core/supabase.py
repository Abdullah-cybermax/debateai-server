import os
from supabase import create_client, Client
from core.logger import logger

supabase_url = 'https://urlsuevahaaldylnarzm.supabase.co'
supabase_key = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVybHN1ZXZhaGFhbGR5bG5hcnptIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2Mzg3OTk0NywiZXhwIjoyMDc5NDU1OTQ3fQ.nsHnMClVaCk6XaQSoANOO_piRNkdFWvUqeaZt1qDhD8'

supabase: Client = create_client(
    supabase_url=supabase_url, supabase_key=supabase_key
)
bucket: str = os.getenv("SUPABASE_BUCKET_NAME")

def upload_pdf_to_supabase(file_data: bytes, file_name: str) -> str:
    try:
        logger.info(f"📤 Uploading PDF to Supabase: {file_name}")

        try:
            existing_files = supabase.storage.from_(bucket).list()

            if any(f["name"] == file_name for f in existing_files):
                supabase.storage.from_(bucket).remove([file_name])
                logger.info(f"🗑️ Removed existing file: {file_name}")
        except Exception as e:
            logger.warning(f"⚠️ Could not check for existing file: {e}")

        res = supabase.storage.from_(bucket).upload(
            file=file_data,
            path=file_name,
            file_options={"content-type": "application/pdf"},
        )

        logger.info(f"✅ PDF uploaded successfully: {file_name}")

        public_url_res = supabase.storage.from_(bucket).get_public_url(file_name)
        public_url = str(public_url_res)

        logger.info(f"🔗 Public URL: {public_url}")
        return public_url

    except Exception as e:
        logger.error(f"❌ Failed to upload PDF to Supabase: {str(e)}")
        if hasattr(e, "response"):
            logger.error(
                f"📄 Response content: {e.response.text if hasattr(e.response, 'text') else 'No response text'}"
            )
        raise
