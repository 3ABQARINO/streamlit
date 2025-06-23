import streamlit as st
import datetime
import pandas as pd
from io import BytesIO

def generate_excel_report(data_dict):
    """
    Generates an Excel report from the provided data dictionary.
    The report will contain the assessment inputs and the final guidance.
    """
    # Prepare data for DataFrame
    report_data = {}
    translated_keys = {
        'caller_type': 'نوع المتصل',
        'relative_type': 'صلة القرابة',
        'caller_name': 'اسم المتصل',
        'caller_phone': 'رقم هاتف المتصل',
        'case_stability': 'استقرار الحالة',
        'willingness_for_treatment': 'الرغبة في العلاج',
        'age': 'العمر',
        'aggression_suicidal': 'سلوك عدواني/أفكار انتحارية',
        'substance_duration_query': 'استفسار عن مدة بقاء المادة',
        'other_entities_unresponsive': 'جهات أخرى غير مستجيبة',
        'suspicion_of_abuse': 'الاشتباه في التعاطي',
        'general_inquiry': 'استفسار عام',
        'appointment_issue': 'مشكلة في الموعد',
        'silent_call': 'مكالمة صامتة',
        'insist_inperson': 'الإصرار على موعد حضوري',
        'final_guidance': 'الإرشادات النهائية' # This will be added later
    }

    # Populate report_data with translated keys
    for key, value in data_dict.items():
        if key in translated_keys:
            report_data[translated_keys[key]] = [str(value)] # Convert to string for display in Excel
        else:
            report_data[key] = [str(value)]

    # Add a placeholder for final guidance, which will be populated in run_app
    report_data['الإرشادات النهائية'] = [""] # Will be updated dynamically

    df = pd.DataFrame(report_data)

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='تقرير التقييم', index=False)
    output.seek(0)
    return output

def get_guidance(form_data):
    """
    Determines the final guidance based on the collected form data.
    """
    guidance_messages = []

    # Guidance based on Case Stability
    if form_data['case_stability'] == "لا":
        guidance_messages.append("الحالة غير مستقرة طبياً. يتطلب ذلك إجراءً فورياً:")
        if form_data['aggression_suicidal'] == "نعم":
            guidance_messages.append("إرشادات: اتصل بسلطات الأمن (911/999) أو الهلال الأحمر فوراً في حالات السلوك العدواني/الأفكار الانتحارية.")
        else:
            guidance_messages.append("إرشادات: اتصل بالهلال الأحمر فوراً للنقل الطبي الطارئ.")
        guidance_messages.append("ملاحظة: للحالات غير المستقرة، يتم تسجيل رقم هاتف المتصل فقط. لا يتم أخذ بيانات شخصية (الاسم، الهوية).")

    elif form_data['case_stability'] == "نعم":
        if form_data['caller_type'] == "بنفسي" or \
           (form_data['caller_type'] == "شخص آخر" and form_data['relative_type'] == "والد/ولي أمر" and form_data['age'] < 18):
            if form_data['willingness_for_treatment'] == "نعم":
                if form_data['insist_inperson'] == "لا":
                    guidance_messages.append("إرشادات: الحالة مستقرة وراغبة في العلاج الافتراضي.")
                    guidance_messages.append("سيتم تحديد موعد افتراضي في عيادة الإدمان بمستشفى صحة الافتراضي. سيتم إرسال رسالة نصية قصيرة (SMS) تحتوي على تفاصيل الموعد خلال 72 ساعة.")
                    guidance_messages.append("**البيانات المطلوبة:** سيتم طلب البيانات الشخصية الكاملة (الاسم، رقم الهوية) لحجز الموعد.")
                else: # Insist on in-person
                    guidance_messages.append("إرشادات: العيادة الافتراضية هي الأولوية للتقييم الأولي. سيتم تحديد موعد افتراضي أولي. إذا دعت الحاجة بعد التقييم، سيتم الإحالة إلى عيادة إرادة الحضورية.")
                    guidance_messages.append("**البيانات المطلوبة:** سيتم طلب البيانات الشخصية الكاملة (الاسم، رقم الهوية) لحجز الموعد.")

            elif form_data['willingness_for_treatment'] == "لا":
                guidance_messages.append("إرشادات: الحالة مستقرة ولكن غير راغبة في العلاج الافتراضي. سيتم تقديم الإرشاد والدعم، ولكن لا يمكن حجز موعد من خلال العيادة الافتراضية.")
                guidance_messages.append("يمكن إحالتك إلى قسم المواعيد (500) لحجز موعد حضوري في عيادات إرادة إذا غيرت رأيك. إذا لم تكن هناك رغبة في أي من الخدمتين، سيتم تقديم إرشاد طبي عام وتثقيف.")
                guidance_messages.append("ملاحظة: لا يتم تسجيل بيانات شخصية (الاسم، الهوية) إذا كان الشخص غير راغب في العلاج.")

        elif form_data['caller_type'] == "شخص آخر" and form_data['relative_type'] == "قريب/صديق آخر" and form_data['age'] >= 18:
            if form_data['willingness_for_treatment'] == "نعم":
                guidance_messages.append("إرشادات: للحالات البالغة التي يتصل بها 'قريب/صديق آخر'، يجب على الشخص الذي يعاني من الإدمان الاتصال بـ 937 بنفسه لحجز موعد.")
                guidance_messages.append("يرجى نصحهم بالاتصال على 937 وطمأنتهم بسرية المعلومات. لا يتم تسجيل بيانات شخصية (الاسم، الهوية) من مكالمتك.")
            else: # Willingness No for Other Relative/Friend
                guidance_messages.append("إرشادات: الشخص الذي يعاني من الإدمان مستقر ولكنه غير راغب في العلاج. انصحهم بالاتصال بـ 937 بأنفسهم وطمأنتهم بسرية المعلومات. قدم الدعم لهم لتغيير حياتهم للأفضل. يمكن أيضاً تزويدك برقم مركز استشارات اللجنة الوطنية لمكافحة المخدرات (1955) إذا كانت العائلة ترغب في النقل القسري (بعد نصح الشخص بالاتصال بـ 937 بنفسه ورفضه).")
                guidance_messages.append("ملاحظة: لا يتم تسجيل بيانات شخصية.")

        # Specific inquiries for stable and willing cases
        if form_data.get('substance_duration_query') == "نعم":
            guidance_messages.append("إرشادات (استفسار عن مدة بقاء المادة):")
            guidance_messages.append("أ. يمكن حجز موعد افتراضي مع استشاري إدمان في عيادة الإدمان بمستشفى صحة الافتراضي.")
            guidance_messages.append("ب. يمكن إحالتك إلى قسم الاستفسارات (500) لحجز موعد حضوري في عيادات إرادة.")
            guidance_messages.append("ملاحظة: لا يتم تسجيل بيانات شخصية (الاسم، الهوية) لهذا الاستفسار المحدد.")

        if form_data.get('other_entities_unresponsive') == "نعم":
            guidance_messages.append("إرشادات (جهات أخرى غير مستجيبة):")
            guidance_messages.append("سيتم تحويلك إلى القسم الإداري للمساعدة في حال عدم تجاوب الجهات الأخرى (مثل مكافحة المخدرات، الأمن).")
            guidance_messages.append("ملاحظة: لا يتم تسجيل بيانات شخصية (الاسم، الهوية) لهذا الاستفسار المحدد.")

        if form_data.get('suspicion_of_abuse') == "نعم":
            guidance_messages.append("إرشادات (الاشتباه في التعاطي):")
            guidance_messages.append("العيادة الافتراضية تقيم الحالات التي لديها أسباب واضحة لتعاطي المواد. للشكوك، يوصى بزيارة حضورية لعيادات إرادة للتقييم وطلب الفحوصات المخبرية.")
            guidance_messages.append("سيتم تحويلك إلى قسم الاستفسارات (500) لحجز موعد حضوري في عيادات إرادة.")
            guidance_messages.append("ملاحظة: لا يتم تسجيل بيانات شخصية (الاسم، الهوية) لهذا الاستفسار المحدد.")

        if form_data.get('general_inquiry') == "نعم":
            guidance_messages.append("إرشادات (استفسار عام عن الإدمان):")
            guidance_messages.append("تحرص وزارة الصحة على تقديم الدعم بسرية تامة لأي شخص يسعى للعلاج. إذا رغب المستفيد في التسجيل في عيادة الإدمان الافتراضية، يمكن تسجيل البيانات. خلاف ذلك، يتم تسجيل رقم هاتف المتصل فقط.")
            guidance_messages.append("سيتم تقديم الإرشاد بناءً على تقييم الحالة.")
            guidance_messages.append("ملاحظة: يتم تسجيل البيانات الشخصية (الاسم، الهوية) فقط إذا رغب المستفيد في التسجيل لموعد.")

        if form_data.get('appointment_issue') == "نعم":
            guidance_messages.append("إرشادات (مشكلة في الموعد/مشكلة فنية):")
            guidance_messages.append("إذا كانت المشكلة خلال 72 ساعة، طمأنهم بأن الرسالة ستصل. إذا تجاوزت 72 ساعة، اتصل فوراً بفريق الجودة على مجموعة الواتساب لتسجيل طلب. سيتم تسجيل نموذج يحتوي على رقم المتصل ونوع الاستفسار فقط.")
            guidance_messages.append("ملاحظة: يتم تسجيل البيانات الشخصية (الاسم، الهوية) لهذه المشكلة.")

    if form_data.get('silent_call') == "نعم":
        guidance_messages.append("إرشادات (مكالمة صامتة):")
        guidance_messages.append("سيتم تقديم رسالة ختامية قياسية: 'عزيزي المتصل، نتشرف بخدمتكم دائماً باستشارات الإدمان الطبية بوزارة الصحة 937. نطمئنكم بسرية المعلومات، ويمكنكم معاودة الاتصال بنا في أي وقت. شكراً لاتصالكم بوزارة الصحة. سيتم تقييمكم.'")
        guidance_messages.append("ملاحظة: هذا لا يتطلب تسجيل في النموذج.")

    return "\n".join(guidance_messages)

def run_app():
    """
    Main function to run the Streamlit application.
    This sets up the title, form, and handles submission based on the Addiction Pathway.
    """
    st.set_page_config(page_title="تقييم مسار الإدمان", layout="centered")

    st.title("نموذج تقييم مسار الإدمان")
    st.markdown("""
    <style>
    /* Custom CSS for a more polished look */
    .stApp {
        background-color: #f0f2f6; /* Light gray background */
        font-family: 'Inter', sans-serif; /* Using Inter font */
    }
    .st-dg { /* Target form container */
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 8px rgba[0,0,0,0.1); /* Subtle shadow */
    }
    .stButton>button {
        background-color: #007bff; /* Blue button for primary actions */
        color: white;
        border-radius: 8px;
        padding: 10px 20px;
        font-size: 16px;
        border: none;
        cursor: pointer;
        transition: background-color 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #0056b3; /* Darker blue on hover */
    }
    .stTextInput>div>div>input, .stSelectbox>div>div>select, .stDateInput>div>div>input {
        border-radius: 8px;
        border: 1px solid #ccc;
        padding: 8px 12px;
        width: 100%; /* Ensure full width for inputs */
    }
    .stRadio>label {
        font-size: 16px;
        margin-bottom: 8px;
    }
    .stRadio>div {
        display: flex;
        flex-direction: column;
    }
    .stRadio>div>label {
        margin-bottom: 5px;
    }
    .stSuccess {
        background-color: #d4edda;
        color: #155724;
        border-radius: 8px;
        padding: 10px;
        border: 1px solid #c3e6cb;
    }
    .stError {
        background-color: #f8d7da;
        color: #721c24;
        border-radius: 8px;
        padding: 10px;
        border: 1px solid #f5c6cb;
    }
    .question-section {
        background-color: #e9ecef;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 20px;
        border-left: 5px solid #007bff;
    }
    </style>
    """, unsafe_allow_html=True)

    # Initialize session state for multi-step form logic
    if 'page' not in st.session_state:
        st.session_state.page = 0
    if 'form_data' not in st.session_state:
        st.session_state.form_data = {}
    if 'current_question_index' not in st.session_state:
        st.session_state.current_question_index = 0

    # Define navigation functions
    def next_page():
        st.session_state.page += 1
        st.session_state.current_question_index = 0 # Reset for new page

    def prev_page():
        st.session_state.page -= 1
        st.session_state.current_question_index = 0 # Reset for new page

    # Page 0: Initial contact information and type of caller
    if st.session_state.page == 0:
        with st.form(key='page0_form'):
            st.header("معلومات الاتصال الأولية")
            st.markdown("<div class='question-section'>", unsafe_allow_html=True)
            caller_type = st.radio(
                "هل تتصل نيابة عن نفسك أم عن شخص آخر؟",
                ("بنفسي", "شخص آخر"), key='p0_q1'
            )
            st.markdown("</div>", unsafe_allow_html=True)

            relative_type = None
            if caller_type == "شخص آخر":
                st.markdown("<div class='question-section'>", unsafe_allow_html=True)
                relative_type = st.radio(
                    "ما هي صلتك بالشخص؟",
                    ("والد/ولي أمر", "قريب/صديق آخر"), key='p0_q2'
                )
                st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("<div class='question-section'>", unsafe_allow_html=True)
            caller_name = st.text_input("اسمك (اختياري)", max_chars=100, key='p0_q3')
            caller_phone = st.text_input("رقم هاتفك (اختياري)", max_chars=20, key='p0_q4')
            st.markdown("</div>", unsafe_allow_html=True)

            submit_p0 = st.form_submit_button("التالي")
            if submit_p0:
                st.session_state.form_data['caller_type'] = caller_type
                st.session_state.form_data['relative_type'] = relative_type
                st.session_state.form_data['caller_name'] = caller_name
                st.session_state.form_data['caller_phone'] = caller_phone
                next_page()
                st.rerun()

    # Page 1: Case Stability and Willingness for Treatment
    elif st.session_state.page == 1:
        with st.form(key='page1_form'):
            st.header("تقييم الحالة - الاستقرار والرغبة في العلاج")

            questions_p1 = []

            # Question 1: Case Stability
            questions_p1.append({
                "id": "case_stability",
                "question": "هل الحالة مستقرة طبياً (لا توجد أعراض انسحاب جسدية أو نفسية حادة)؟",
                "options": ("نعم", "لا")
            })

            # Question 2: Willingness for Treatment (conditional)
            if st.session_state.form_data['caller_type'] == "بنفسي" or \
               (st.session_state.form_data['caller_type'] == "شخص آخر" and st.session_state.form_data['relative_type'] == "والد/ولي أمر"):
                questions_p1.append({
                    "id": "willingness_for_treatment",
                    "question": "هل توجد رغبة في العلاج؟",
                    "options": ("نعم", "لا")
                })
            elif st.session_state.form_data['caller_type'] == "شخص آخر" and st.session_state.form_data['relative_type'] == "قريب/صديق آخر":
                questions_p1.append({
                    "id": "willingness_for_treatment",
                    "question": "هل لدى الشخص الذي يعاني من الإدمان رغبة في العلاج الافتراضي؟ (يرجى نصحه بالاتصال على 937 إن كان ذلك ممكناً)",
                    "options": ("نعم", "لا")
                })

            # Question 3: Age
            if st.session_state.form_data['caller_type'] == "شخص آخر":
                questions_p1.append({
                    "id": "age",
                    "question": "عمر الشخص الذي يعاني من الإدمان",
                    "type": "number_input",
                    "min_value": 1, "max_value": 120, "value": 25
                })
            else:
                questions_p1.append({
                    "id": "age",
                    "question": "عمرك",
                    "type": "number_input",
                    "min_value": 1, "max_value": 120, "value": 25
                })

            # Display questions one by one
            for i, q in enumerate(questions_p1):
                if i == st.session_state.current_question_index:
                    st.markdown("<div class='question-section'>", unsafe_allow_html=True)
                    if q.get("type") == "number_input":
                        st.session_state.form_data[q["id"]] = st.number_input(
                            q["question"], min_value=q["min_value"], max_value=q["max_value"],
                            value=q["value"], key=f'p1_q{i}'
                        )
                    else:
                        st.session_state.form_data[q["id"]] = st.radio(
                            q["question"], q["options"], key=f'p1_q{i}'
                        )
                    st.markdown("</div>", unsafe_allow_html=True)
                    break # Only display one question at a time

            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("السابق"):
                    prev_page()
                    st.rerun()
            with col2:
                if st.session_state.current_question_index < len(questions_p1) - 1:
                    if st.form_submit_button("التالي"):
                        st.session_state.current_question_index += 1
                        st.rerun()
                else:
                    if st.form_submit_button("التالي"):
                        next_page()
                        st.rerun()


    # Page 2: Specific Scenarios and Guidance
    elif st.session_state.page == 2:
        with st.form(key='page2_form'):
            st.header("تقييم السيناريو المحدد")

            questions_p2 = []

            # Conditional question: Aggression/Suicidal thoughts
            if st.session_state.form_data.get('case_stability') == "لا":
                questions_p2.append({
                    "id": "aggression_suicidal",
                    "question": "هل يظهر الشخص سلوكاً عدوانياً أو لديه أفكار انتحارية/نية لإيذاء الآخرين؟",
                    "options": ("نعم", "لا")
                })
            elif st.session_state.form_data.get('case_stability') == "نعم" and \
                 st.session_state.form_data.get('willingness_for_treatment') == "نعم":
                # Questions for stable and willing cases
                questions_p2.append({
                    "id": "insist_inperson",
                    "question": "هل يصر الشخص على موعد حضوري بدلاً من الموعد الافتراضي؟",
                    "options": ("نعم", "لا")
                })
                questions_p2.append({
                    "id": "substance_duration_query",
                    "question": "هل تستفسر عن مدة بقاء مادة معينة في الدم أو البول؟",
                    "options": ("نعم", "لا")
                })
                questions_p2.append({
                    "id": "other_entities_unresponsive",
                    "question": "هل اتصلت بجهات أخرى (مثل مكافحة المخدرات، الأمن) ولم يتم التجاوب؟",
                    "options": ("نعم", "لا")
                })
                questions_p2.append({
                    "id": "suspicion_of_abuse",
                    "question": "هل تشك في أن شخصاً ما يتعاطى المواد (مثل أب يشك في ابنه)؟",
                    "options": ("نعم", "لا")
                })
                questions_p2.append({
                    "id": "general_inquiry",
                    "question": "هل تقوم باستفسار عام حول الإدمان؟",
                    "options": ("نعم", "لا")
                })
                questions_p2.append({
                    "id": "appointment_issue",
                    "question": "هل سبق لك حجز موعد افتراضي ولكن لم تصلك رسالة خلال 72 ساعة، أو واجهت مشكلة فنية، أو لم تصلك رسالة الوصفة؟",
                    "options": ("نعم", "لا")
                })
            elif st.session_state.form_data.get('case_stability') == "نعم" and \
                 st.session_state.form_data.get('willingness_for_treatment') == "لا" and \
                 st.session_state.form_data.get('caller_type') == "شخص آخر" and \
                 st.session_state.form_data.get('relative_type') == "قريب/صديق آخر":
                st.markdown("<div class='question-section'>", unsafe_allow_html=True)
                st.write("بما أن الشخص الذي يعاني من الإدمان غير راغب في العلاج وأنت 'قريب/صديق آخر'، فإن التدخل المباشر لحجز موعد غير ممكن من خلال هذه العيادة الافتراضية. سيتم تزويدك بالإرشادات والموارد لتقديم الدعم.")
                st.markdown("</div>", unsafe_allow_html=True)
                # No further questions in this specific branch, go straight to submission for guidance.
                questions_p2.append({"id": "dummy_question", "question": "لا توجد أسئلة إضافية في هذا المسار. يرجى إرسال التقييم للحصول على الإرشادات.", "options": ["موافق"]}) # Dummy to ensure form can be submitted

            # Silent call question (always present)
            questions_p2.append({
                "id": "silent_call",
                "question": "هل هذه مكالمة صامتة (من البداية أو أثناء المحادثة)؟",
                "options": ("نعم", "لا")
            })

            # Display questions one by one
            for i, q in enumerate(questions_p2):
                if i == st.session_state.current_question_index:
                    st.markdown("<div class='question-section'>", unsafe_allow_html=True)
                    st.session_state.form_data[q["id"]] = st.radio(
                        q["question"], q["options"], key=f'p2_q{i}'
                    )
                    st.markdown("</div>", unsafe_allow_html=True)
                    break # Only display one question at a time

            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("السابق"):
                    prev_page()
                    st.rerun()
            with col2:
                if st.session_state.current_question_index < len(questions_p2) - 1:
                    if st.form_submit_button("التالي"):
                        st.session_state.current_question_index += 1
                        st.rerun()
                else:
                    if st.form_submit_button("إرسال التقييم"):
                        next_page()
                        st.rerun()


    # Page 3: Displaying Results and Guidance
    elif st.session_state.page == 3:
        st.header("نتائج التقييم والإرشادات")
        st.write("شكراً لإكمال التقييم. فيما يلي الإرشادات بناءً على إجاباتك:")

        final_guidance_text = get_guidance(st.session_state.form_data)
        st.info(final_guidance_text)

        st.write("---")
        st.subheader("ملخص مدخلاتك:")
        # Translate keys for display
        translated_keys = {
            'caller_type': 'نوع المتصل',
            'relative_type': 'صلة القرابة',
            'caller_name': 'اسم المتصل',
            'caller_phone': 'رقم هاتف المتصل',
            'case_stability': 'استقرار الحالة',
            'willingness_for_treatment': 'الرغبة في العلاج',
            'age': 'العمر',
            'aggression_suicidal': 'سلوك عدواني/أفكار انتحارية',
            'substance_duration_query': 'استفسار عن مدة بقاء المادة',
            'other_entities_unresponsive': 'جهات أخرى غير مستجيبة',
            'suspicion_of_abuse': 'الاشتباه في التعاطي',
            'general_inquiry': 'استفسار عام',
            'appointment_issue': 'مشكلة في الموعد',
            'silent_call': 'مكالمة صامتة',
            'insist_inperson': 'الإصرار على موعد حضوري'
        }
        for key, value in st.session_state.form_data.items():
            display_key = translated_keys.get(key, key.replace('_', ' ').title())
            st.write(f"**{display_key}:** {value}")

        # Add final guidance to form_data for Excel export
        st.session_state.form_data['final_guidance'] = final_guidance_text

        # Download button for Excel report
        excel_data = generate_excel_report(st.session_state.form_data)
        st.download_button(
            label="تنزيل تقرير التقييم (Excel)",
            data=excel_data,
            file_name="تقرير_تقييم_الإدمان.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        if st.button("بدء تقييم جديد"):
            st.session_state.page = 0
            st.session_state.form_data = {}
            st.session_state.current_question_index = 0
            st.rerun()

# Run the Streamlit app
if __name__ == '__main__':
    run_app()