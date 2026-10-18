import io
import re
from datetime import date
import pandas as pd
import streamlit as st
from database import init_db, upsert_vehicle, save_cleaning, read_cleanings, read_vehicles, set_paid, delete_cleaning
from ocr import extract_fleet_numbers

st.set_page_config(page_title='VanTrack | Campervan Cleaning', page_icon='🚐', layout='wide')
init_db()
RATE_CENTS = 3000

st.markdown('''<style>
.block-container {padding-top: 1.5rem; max-width: 1100px;}
[data-testid="stMetric"] {background: #2986cc; padding: 14px; border-radius: 12px;}
</style>''', unsafe_allow_html=True)

st.title('🚐 VanTrack')
st.caption('Campervan cleaning inventory & personal earnings')
page = st.radio('Navigate', ['📊 Dashboard', '📷 Scan & Log', '🚐 Vehicles', '💰 Earnings', '📋 History'], horizontal=True, label_visibility='collapsed')

jobs = read_cleanings()
vehicles = read_vehicles()

def dollars(cents):
    return f'A${cents / 100:,.2f}'

if page == '📊 Dashboard':
    today = date.today().isoformat()
    today_jobs = jobs[jobs['cleaning_date'] == today] if not jobs.empty else jobs
    cols = st.columns(4)
    cols[0].metric('Cleanings today', len(today_jobs))
    cols[1].metric('My earnings today', dollars(int(today_jobs['my_share_cents'].sum())))
    cols[2].metric('Total jobs', len(jobs))
    cols[3].metric('Unpaid earnings', dollars(int(jobs.loc[jobs['paid'] == 0, 'my_share_cents'].sum())) if not jobs.empty else 'A$0.00')
    st.subheader('Recent jobs')
    if jobs.empty:
        st.info('No cleanings saved yet. Open Scan & Log to add your first campervan.')
    else:
        show = jobs[['cleaning_date', 'fleet_number', 'cleaners', 'my_share_cents', 'paid']].head(10).copy()
        show['my_share'] = show.pop('my_share_cents').map(dollars)
        show['paid'] = show['paid'].map({0: 'Unpaid', 1: 'Paid'})
        st.dataframe(show, hide_index=True, use_container_width=True)

elif page == '📷 Scan & Log':
    st.subheader('1. Identify the campervan')
    source = st.radio('Image source', ['Camera', 'Upload photo', 'Type manually'], horizontal=True)
    image = None
    if source == 'Camera':
        image = st.camera_input('Photograph the six-digit fleet number')
    elif source == 'Upload photo':
        image = st.file_uploader('Choose a vehicle photo', type=['jpg', 'jpeg', 'png'])
    if image is not None:
        b = image.getvalue()
        if st.button('🔍 Detect fleet number'):
            try:
                with st.spinner('Reading fleet number...'):
                    guesses = extract_fleet_numbers(io.BytesIO(b))
                st.session_state['ocr_guesses'] = guesses
                if guesses:
                    st.session_state['fleet_input'] = guesses[0]
                    st.success('Detected: ' + ', '.join(guesses) + '. Check the number before saving.')
                else:
                    st.warning('No six-digit number found. Please enter it manually.')
            except Exception as exc:
                st.error(f'OCR failed: {exc}')
    guesses = st.session_state.get('ocr_guesses', [])
    if guesses:
        st.caption('Possible detected fleet numbers: ' + ', '.join(guesses))
    st.text_input('Fleet number (verify or correct)', placeholder='e.g. 362597', key='fleet_input', max_chars=6)
    st.subheader('2. Record cleaning')
    with st.form('cleaning_form', clear_on_submit=False):
        job_date = st.date_input('Date cleaned', value=date.today(), max_value=date.today())
        cleaners = st.number_input('Total people who cleaned the campervan (including you)', min_value=1, max_value=30, value=1, step=1)
        brand = st.text_input('Brand / rental company (optional)', placeholder='e.g. THL / Action')
        model = st.text_input('Vehicle model (optional)', placeholder='e.g. DELM')
        note = st.text_area('Job notes (optional)', placeholder='e.g. Interior clean, laundry and vehicle parking')
        st.info(f'Total job fee: {dollars(RATE_CENTS)}  |  Your share: {dollars(round(RATE_CENTS / cleaners))}  |  Split equally between {cleaners} person(s)')
        submitted = st.form_submit_button('💾 Save cleaning job', type='primary', use_container_width=True)
        if submitted:
            fleet = st.session_state.get('fleet_input', '').strip()
            if not re.fullmatch(r'\d{6}', fleet):
                st.error('Enter a valid 6-digit fleet number.')
            else:
                upsert_vehicle(fleet, brand, model)
                job_id = save_cleaning(fleet, job_date.isoformat(), int(cleaners), RATE_CENTS, note)
                st.success(f'Saved job #{job_id}: {fleet}. Your share: {dollars(round(RATE_CENTS / cleaners))}.')
                st.caption('Multiple cleaning jobs for the same fleet number are allowed, including on different dates.')

elif page == '🚐 Vehicles':
    st.subheader('Fleet inventory')
    st.caption('Each fleet number appears once, even if you clean that campervan many times.')
    search = st.text_input('Search fleet number or vehicle model')
    if not vehicles.empty:
        view = vehicles.copy()
        if search:
            mask = view[['fleet_number', 'brand', 'model']].fillna('').astype(str).apply(lambda col: col.str.contains(search, case=False, regex=False)).any(axis=1)
            view = view[mask]
        view['earned'] = view.pop('total_earned_cents').map(dollars)
        st.dataframe(view[['fleet_number', 'brand', 'model', 'times_cleaned', 'earned', 'notes']], hide_index=True, use_container_width=True)
        st.metric('Unique campervans', len(vehicles))
    else:
        st.info('The inventory will populate automatically as you save cleaning jobs.')

elif page == '💰 Earnings':
    st.subheader('My earnings')
    if jobs.empty:
        st.info('Save a cleaning job to see your earnings.')
    else:
        a, b, c = st.columns(3)
        a.metric('Earned', dollars(int(jobs['my_share_cents'].sum())))
        b.metric('Paid', dollars(int(jobs.loc[jobs['paid'] == 1, 'my_share_cents'].sum())))
        c.metric('Outstanding', dollars(int(jobs.loc[jobs['paid'] == 0, 'my_share_cents'].sum())))
        df = jobs.copy()
        df['cleaning_date'] = pd.to_datetime(df['cleaning_date'])
        df['week'] = df['cleaning_date'].dt.to_period('W-SUN').astype(str)
        weekly = df.groupby('week')['my_share_cents'].sum().div(100)
        st.subheader('Weekly earnings (A$)')
        st.bar_chart(weekly)
        st.caption('Earnings here are expected cleaning fees, not confirmation that your employer has paid them.')

elif page == '📋 History':
    st.subheader('Cleaning history')
    if jobs.empty:
        st.info('No cleaning history yet.')
    else:
        df = jobs.copy()
        df['my_share'] = df['my_share_cents'].map(dollars)
        df['job_fee'] = df['total_fee_cents'].map(dollars)
        df['paid'] = df['paid'].map({0: 'Unpaid', 1: 'Paid'})
        st.dataframe(df[['id','cleaning_date','fleet_number','cleaners','job_fee','my_share','paid','notes']], hide_index=True, use_container_width=True)
        st.download_button('⬇️ Export CSV', jobs.to_csv(index=False).encode('utf-8'), file_name='vantrack_cleanings.csv', mime='text/csv')
        st.subheader('Update a job')
        job_id = st.selectbox('Select job ID', options=jobs['id'].tolist(), format_func=lambda i: f'#{i} — {jobs.loc[jobs.id == i, "fleet_number"].iloc[0]}')
        selected = jobs.loc[jobs.id == job_id].iloc[0]
        col1, col2 = st.columns(2)
        if col1.button('✅ Mark paid' if not selected['paid'] else '↩️ Mark unpaid'):
            set_paid(job_id, not bool(selected['paid']))
            st.rerun()
        with col2.popover('🗑️ Delete job'):
            st.warning('This permanently deletes the selected cleaning job.')
            if st.button('Confirm delete', type='primary'):
                delete_cleaning(job_id)
                st.rerun()

st.divider()
st.caption('VanTrack v1 • A$30 per cleaning • Payment divided equally among all cleaners • Data stored locally in SQLite')
