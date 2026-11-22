
import streamlit as st
import json

from src.document_reader import (
    process_document,
    process_pasted_text,
    DocumentProcessingError
)

from src.ai_extractor import (
    extract_document,
    ExtractionError
)

from src.validator import (
    validate_invoice,
    invoice_to_json,
    get_missing_fields
)

from src.utils import (
    compare_prompt_versions,
    get_best_prompt_version
)


# ==========================================
# PAGE CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="Smart Invoice & Receipt Extractor",
    page_icon="📄",
    layout="wide"
)

st.title("📄 Smart Invoice & Receipt Extractor")

st.write(
    "Extract structured information from invoices and receipts "
    "and evaluate prompt performance."
)


# ==========================================
# HELPER FUNCTION
# ==========================================

def read_json_upload(uploaded_file):
    """Reads and validates an uploaded JSON file."""

    if uploaded_file is None:
        raise ValueError("Please upload the required JSON file.")

    try:
        data = json.load(uploaded_file)

    except json.JSONDecodeError as error:
        raise ValueError(
            f"Invalid JSON file: {error}"
        ) from error

    if not isinstance(data, dict):
        raise ValueError(
            "The JSON file must contain a JSON object."
        )

    if "data" in data and isinstance(data["data"], dict):
        data = data["data"]

    return data


# ==========================================
# MAIN TABS
# ==========================================

extractor_tab, evaluation_tab = st.tabs(
    ["📄 Invoice Extractor", "📊 Prompt Evaluation"]
)


# ==========================================
# TAB 1: INVOICE EXTRACTOR
# ==========================================

with extractor_tab:

    st.header("Invoice and Receipt Extraction")

    # Sidebar settings
    st.sidebar.header("Extraction Settings")

    prompt_version = st.sidebar.selectbox(
        "Select Prompt Version",
        ["v1", "v2", "v3", "final"],
        index=3
    )

    # Gemini is now the default mode
    extraction_mode = st.sidebar.selectbox(
        "Extraction Mode",
        ["gemini", "mock"],
        index=0
    )

    if extraction_mode == "mock":
        st.warning(
            "Mock mode: Fixed sample data is used. "
            "Your uploaded document is not actually analyzed."
        )

    else:
        st.success(
            "Gemini mode: Your actual document will be analyzed by AI."
        )

    # --------------------------------------
    # DOCUMENT INPUT
    # --------------------------------------

    st.subheader("1. Provide your document")

    input_method = st.radio(
        "Choose input method",
        ["Upload Document", "Paste Text"],
        horizontal=True
    )

    if input_method == "Upload Document":

        uploaded_file = st.file_uploader(
            "Upload invoice or receipt",
            type=["pdf", "jpg", "jpeg", "png"],
            key="invoice_upload"
        )

        if uploaded_file is not None:

            st.success(f"Uploaded: {uploaded_file.name}")

            if st.button(
                "Process Document",
                type="primary"
            ):

                try:
                    document = process_document(
                        uploaded_file.name,
                        uploaded_file.getvalue()
                    )

                    st.session_state["document"] = document

                    # Clear previous extraction results
                    st.session_state.pop("validated_data", None)
                    st.session_state.pop("extraction_result", None)

                    st.success("Document processed successfully.")

                    if document.get("warnings"):
                        for warning in document["warnings"]:
                            st.warning(warning)

                except DocumentProcessingError as error:
                    st.error(str(error))

                except Exception as error:
                    st.error(f"Unexpected error: {error}")

    else:

        pasted_text = st.text_area(
            "Paste invoice or receipt text",
            height=200,
            placeholder="Enter invoice or receipt details..."
        )

        if st.button(
            "Process Text",
            type="primary"
        ):

            if not pasted_text.strip():
                st.warning("Please enter some text first.")

            else:
                document = process_pasted_text(pasted_text)

                st.session_state["document"] = document

                st.session_state.pop("validated_data", None)
                st.session_state.pop("extraction_result", None)

                st.success("Text processed successfully.")

    # --------------------------------------
    # AI EXTRACTION
    # --------------------------------------

    if "document" in st.session_state:

        st.divider()

        st.subheader("2. Run AI Extraction")

        if st.button(
            "Run Extraction",
            type="primary"
        ):

            try:

                with st.spinner(
                    "Analyzing your document..."
                ):

                    extraction_result = extract_document(
                        document=st.session_state["document"],
                        prompt_version=prompt_version,
                        mode=extraction_mode
                    )

                    validated_data = validate_invoice(
                        extraction_result["data"]
                    )

                    st.session_state["validated_data"] = validated_data

                    st.session_state["extraction_result"] = extraction_result

                st.success(
                    "Extraction and validation completed!"
                )

            except ExtractionError as error:
                st.error(str(error))

            except Exception as error:
                st.error(
                    f"Processing failed: {error}"
                )

    # --------------------------------------
    # DISPLAY RESULTS
    # --------------------------------------

    if "validated_data" in st.session_state:

        invoice = st.session_state["validated_data"]

        extraction_result = st.session_state["extraction_result"]

        st.divider()

        st.header("3. Extraction Results")

        st.caption(
            f"Extraction mode: {extraction_result['mode'].upper()}"
        )

        st.info(extraction_result["message"])

        # Summary metrics
        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Document Type",
            invoice.document_type.title()
        )

        col2.metric(
            "Total Amount",
            (
                f"{invoice.currency} {invoice.total:,.2f}"
                if invoice.currency and invoice.total is not None
                else str(invoice.total)
            )
        )

        col3.metric(
            "Number of Items",
            len(invoice.items)
        )

        # Vendor details
        st.subheader("Vendor Details")

        vendor_col1, vendor_col2 = st.columns(2)

        vendor_col1.write(
            f"**Vendor Name:** {invoice.vendor.name or 'Not available'}"
        )

        vendor_col2.write(
            f"**Tax ID:** {invoice.vendor.tax_id or 'Not available'}"
        )

        st.write(
            f"**Address:** {invoice.vendor.address or 'Not available'}"
        )

        st.write(
            f"**Contact:** {invoice.vendor.contact or 'Not available'}"
        )

        # Document details
        st.subheader("Document Details")

        details_col1, details_col2 = st.columns(2)

        details_col1.write(
            f"**Document Number:** {invoice.document_number or 'Not available'}"
        )

        details_col2.write(
            f"**Document Date:** {invoice.document_date or 'Not available'}"
        )

        st.write(
            f"**Currency:** {invoice.currency or 'Not available'}"
        )

        # Items
        st.subheader("Extracted Items")

        if invoice.items:

            items_data = [
                item.model_dump()
                for item in invoice.items
            ]

            st.dataframe(
                items_data,
                use_container_width=True,
                hide_index=True
            )

        else:
            st.info("No line items found.")

        # Financial summary
        st.subheader("Financial Summary")

        financial_data = {
            "Subtotal": invoice.subtotal,
            "Discount": invoice.discount,
            "Tax": invoice.tax,
            "Tax Rate": invoice.tax_rate,
            "Additional Charges": invoice.additional_charges,
            "Total": invoice.total
        }

        st.table(financial_data)

        # Missing fields
        st.subheader("Missing Field Detection")

        missing_fields = get_missing_fields(invoice)

        if missing_fields:

            st.warning(
                f"{len(missing_fields)} important fields are missing."
            )

            for field in missing_fields:
                st.write(f"- {field}")

        else:
            st.success("All important fields are available.")

        # JSON output
        st.divider()

        st.subheader("4. JSON Output")

        json_output = invoice_to_json(invoice)

        st.code(
            json_output,
            language="json"
        )

        st.download_button(
            label="⬇️ Download JSON",
            data=json_output,
            file_name="extracted_invoice.json",
            mime="application/json"
        )


# ==========================================
# TAB 2: PROMPT EVALUATION
# ==========================================

with evaluation_tab:

    st.header("Prompt Performance Evaluation")

    st.write(
        "Compare the extracted results of V1, V2 and V3 "
        "against the expected ground-truth JSON."
    )

    st.info(
        "Upload JSON files containing the extracted invoice data "
        "for each prompt version. This evaluation does not call Gemini."
    )

    st.subheader("1. Upload Ground Truth")

    expected_file = st.file_uploader(
        "Expected output JSON",
        type=["json"],
        key="expected_json"
    )

    st.subheader("2. Upload Prompt Outputs")

    col1, col2, col3 = st.columns(3)

    with col1:
        v1_file = st.file_uploader(
            "V1 output JSON",
            type=["json"],
            key="v1_json"
        )

    with col2:
        v2_file = st.file_uploader(
            "V2 output JSON",
            type=["json"],
            key="v2_json"
        )

    with col3:
        v3_file = st.file_uploader(
            "V3 output JSON",
            type=["json"],
            key="v3_json"
        )

    if st.button(
        "Compare Prompt Versions",
        type="primary"
    ):

        if not all([
            expected_file,
            v1_file,
            v2_file,
            v3_file
        ]):

            st.error(
                "Please upload the expected JSON and all three prompt outputs."
            )

        else:

            try:

                expected_data = read_json_upload(expected_file)

                prompt_outputs = {
                    "v1": read_json_upload(v1_file),
                    "v2": read_json_upload(v2_file),
                    "v3": read_json_upload(v3_file)
                }

                comparison = compare_prompt_versions(
                    expected_data,
                    prompt_outputs
                )

                best_version = get_best_prompt_version(
                    comparison
                )

                st.session_state["comparison"] = comparison

                st.session_state["best_version"] = best_version

                st.success("Prompt comparison completed!")

            except (ValueError, TypeError) as error:
                st.error(str(error))

            except Exception as error:
                st.error(
                    f"Could not compare prompt outputs: {error}"
                )

    # --------------------------------------
    # COMPARISON RESULTS
    # --------------------------------------

    if "comparison" in st.session_state:

        comparison = st.session_state["comparison"]

        best_version = st.session_state["best_version"]

        st.divider()

        st.subheader("3. Comparison Results")

        col1, col2, col3 = st.columns(3)

        for column, version in zip(
            [col1, col2, col3],
            ["v1", "v2", "v3"]
        ):

            result = comparison[version]

            column.metric(
                version.upper() + " Accuracy",
                f"{result['accuracy']}%"
            )

            column.caption(
                f"{result['correct_fields']} / "
                f"{result['total_fields']} fields correct"
            )

        st.success(
            f"Best-performing prompt: {best_version.upper()}"
        )

        # Comparison table
        st.subheader("Accuracy Summary")

        summary_rows = []

        for version, result in comparison.items():

            summary_rows.append({
                "Prompt": version.upper(),
                "Total Fields": result["total_fields"],
                "Correct Fields": result["correct_fields"],
                "Incorrect Fields": result["incorrect_fields"],
                "Accuracy (%)": result["accuracy"]
            })

        st.dataframe(
            summary_rows,
            use_container_width=True,
            hide_index=True
        )

        # Field-level results
        st.subheader("4. Field-Level Analysis")

        selected_version = st.selectbox(
            "Select prompt to inspect",
            ["v1", "v2", "v3"]
        )

        field_results = comparison[selected_version]["field_results"]

        field_rows = []

        for field, details in field_results.items():

            field_rows.append({
                "Field": field,
                "Expected": str(details["expected"]),
                "Extracted": str(details["actual"]),
                "Status": (
                    "Correct" if details["correct"]
                    else "Incorrect"
                )
            })

        st.dataframe(
            field_rows,
            use_container_width=True,
            hide_index=True
        )

        # Export comparison
        comparison_json = json.dumps(
            comparison,
            indent=4,
            ensure_ascii=False
        )

        st.download_button(
            "⬇️ Download Comparison Results",
            data=comparison_json,
            file_name="prompt_comparison.json",
            mime="application/json"
        )
