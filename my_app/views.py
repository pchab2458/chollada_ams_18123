from .forms import PaymentForm
from .forms import Elec_cpu_change, Water_cpu_change
from .forms import MaintenanceForm
from .models import Extra, Room, Room_type
from django.utils.dateparse import parse_datetime
from django.utils.timezone import is_aware, make_aware
from django.shortcuts import get_object_or_404
from .forms import BillForm
from my_app.models import Billing
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from .forms import TenantCreateForm, TenantProfileCreateForm
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views import generic
from django.shortcuts import render
from users.forms import CustomUserCreationForm
from my_app.models import TenantProfile
from django.contrib.auth import get_user_model
import random
import calendar
import datetime
import decimal
import GV



CUser = get_user_model()


class CholladaHomePage(TemplateView):
    template_name = 'my_app/Chollada_Apartment.html'  # default template if not defined in the url


@login_required
def gateway(request):
    return render(request, 'my_app/admin_page.html')


@login_required
def admin_page(request):
    return render(request, 'my_app/admin_page.html')


@login_required
def create_contract(request):
    if request.method == 'POST':
        tenant_form = TenantCreateForm(data=request.POST)
        # tenant_profile_form = TenantProfileCreateForm(data=request.POST, files=request.FILES)
        tenant_profile_form = TenantProfileCreateForm(data=request.POST, files=request.FILES)

        if tenant_form.is_valid() and tenant_profile_form.is_valid():

            # Create a new tenant object but avoid saving it yet
            new_tenant = tenant_form.save(commit=False)

            # Set the chosen password
            # new_tenant.set_password(tenant_form.cleaned_data['password'])
            new_tenant.set_password(tenant_form.clean_password2())

            # Save the new_tenant object
            new_tenant.save()

            # Create a new tenantprofile object but avoid saving it yet
            tenant_profile = tenant_profile_form.save(commit=False)  # save_m2m() added to tenant_profile_form

            # Set the chosen tenant field
            tenant_profile.tenant = new_tenant

            # ------------------------------------------
            # provide initial value to certain fields before saving to DB
            tenant_profile.elec_unit = 0
            tenant_profile.water_unit = 0
            tenant_profile.misc_cost = 0
            # -----------------------------------------

            # Save the tenantprofile object
            tenant_profile.save()

            # Save the ManyToMany
            tenant_profile_form.save_m2m()

            messages.success(request, 'Profile has been updated successfully')

            return HttpResponseRedirect(reverse_lazy('admin_page'))
        else:
            messages.error(request, 'Error updating your tenant_profile')

    else:
        tenant_form = TenantCreateForm()
        # tenant_profile_form = TenantProfileCreateForm()
        tenant_profile_form = TenantProfileCreateForm()

    return render(request, 'my_app/create_contract.html',
                  {'section': 'new_contract',
                   'tenant_form': tenant_form,
                   'tenant_profile_form': tenant_profile_form
                   }
                  )


# @login_required # ????? #ORIGINAL
def create_bill(room_no):
    pf = get_object_or_404(TenantProfile, room_no__room_no=room_no)
    tname = pf.tenant.first_name + ' ' + pf.tenant.last_name

    rno = pf.room_no.room_no
    adj = pf.adjust

    exd = {}
    exd.setdefault('Electricity CPU', 0)
    exd.setdefault('Water CPU', 0)
    exd.setdefault('Garbage', 0)
    exd.setdefault('Parking', 0)
    exd.setdefault('Wifi', 0)
    exd.setdefault('Cable TV', 0)
    exd.setdefault('Bed', 0)
    exd.setdefault('Bed accessories', 0)
    exd.setdefault('Dressing Table', 0)
    exd.setdefault('Clothing Cupboard', 0)
    exd.setdefault('TV Table', 0)
    exd.setdefault('Fridge', 0)
    exd.setdefault('Air-Conditioner', 0)

    for e in pf.extra.all():
        exd.update({e.desc: e.cpu})

    room_cost = pf.room_no.room_type.rate
    room_acc_cost = exd['Bed'] + exd['Bed accessories'] + exd['Dressing Table'] \
                    + exd['Clothing Cupboard'] + exd['TV Table'] + exd['Fridge'] \
                    + exd['Air-Conditioner']

    elec_cost = exd['Electricity CPU'] * pf.elec_unit
    water_cost = exd['Water CPU'] * pf.water_unit

    com_ser_cost = pf.elec_unit * GV.COMMOM_SERVICE_CPU

    oth_ser_cost = exd['Garbage'] + exd['Parking'] + exd['Wifi'] + exd['Cable TV']
    ovd_amt = pf.cum_ovd

    # -----------------------
    late_f = pf.late_fee
    maint_c = pf.maint_cost

    # RESET pf.late_fee & pf.maint_cost TO O TO BE READY FOR NEXT CYCLE
    pf.late_fee = 0
    pf.maint_cost = 0
    # -----------------------

    total = room_cost + room_acc_cost + elec_cost + water_cost + com_ser_cost + oth_ser_cost + ovd_amt + adj + late_f + maint_c

    # CREATE PRELIMINARY BILL OBJECT **************
    new_bill = Billing(bill_ref=get_ref_string(),
                       bill_date=datetime.datetime.now().date(),  # SUPPLY BILL DATE
                       tenant_name=tname,
                       room_no=rno,
                       room_cost=room_cost,
                       room_acc_cost=room_acc_cost,
                       electricity_cost=elec_cost,
                       water_cost=water_cost,
                       common_ser_cost=com_ser_cost,
                       other_ser_cost=oth_ser_cost,
                       overdue_amount=ovd_amt,

                       # -----------------------
                       late_fee=late_f,
                       maint_cost=maint_c,
                       # -----------------------

                       adjust=adj,
                       bill_total=total,

                       )

    # SAVE TENANTPROFILE OBJECT TO DB
    pf.save()

    # ADJUST PRELIMINARY BILL OBJECT
    adjust_bill(pf, new_bill)


def adjust_bill(pf, new_bill):
    tn_bill = new_bill

    bref = tn_bill.bill_ref
    bdate = tn_bill.bill_date
    # bupd # TO BE FILLED WHEN SAVED
    # bstat # TO BE FILLED WHEN SAVED
    tname = tn_bill.tenant_name
    rno = tn_bill.room_no
    room_cost = tn_bill.room_cost
    room_acc_cost = tn_bill.room_acc_cost
    elec_cost = tn_bill.electricity_cost
    water_cost = tn_bill.water_cost
    com_ser_cost = tn_bill.common_ser_cost
    oth_ser_cost = tn_bill.other_ser_cost
    ovd_amt = tn_bill.overdue_amount
    adj = tn_bill.adjust
    # total = tn_bill.bill_total # TO BE ADJUSTED IF REQUIRED

    # pay_date # TO BE FILLED AT PAYMENT
    # pay_amt #TO BE FILL AT PAYMENT
    # bf #TO BE FILLED AT PAYMENT

    late_f = tn_bill.late_fee
    maint_c = tn_bill.maint_cost

    sdate = pf.start_date  # FROM pf

    start_day = sdate.day
    bill_day = bdate.day

    start_m = sdate.month
    bill_m = bdate.month

    number_of_day_in_start_month = calendar.monthrange(sdate.year, sdate.month)[1]
    nodsm = number_of_day_in_start_month
    number_of_day_in_bill_month = calendar.monthrange(bdate.year, bdate.month)[1]
    nodbm = number_of_day_in_bill_month

    # Original Version-Bug !!! =====================================================================================
    #    if abs(start_m - bill_m) == 0:
    #        tbd = number_of_day_in_bill_month - start_day + 1  # SPECIAL CASE 1
    #    elif abs(start_m - bill_m) == 1 and start_day >= bill_day:
    #        tbd = number_of_day_in_bill_month + (number_of_day_in_start_month - start_day + 1)  # SPECIAL CASE 2
    #    else:
    #        tbd = number_of_day_in_bill_month  # ONGOING CASE
    # ======================================================================================

    # Revised-Corrected Version
    # EDITED CORRECTED  --------------------------------------------------------------------
    #    tbd = 0
    #    if sdate.year == bdate.year:
    #        if abs(start_m - bill_m) == 0:  # SAME MONTH
    #            tbd = number_of_day_in_bill_month - start_day + 1  # SPECIAL CASE 1
    #        elif abs(start_m - bill_m) == 1 and start_day >= bill_day:
    #            tbd = number_of_day_in_bill_month + (number_of_day_in_start_month - start_day + 1)  # SPECIAL CASE 2
    #    else:
    #        if start_m == 12 and sdate.year + 1 == bdate.year and start_day >= bill_day:  # DECEMBER/YEAR CHANGE
    #            tbd = number_of_day_in_bill_month + (number_of_day_in_start_month - start_day + 1)  # SPECIAL CASE 3
    #        else:
    #            tbd = number_of_day_in_bill_month  # ONGOING CASE
    #

    # -------------- TEST 2 final--------------------------------------------------------------
    tbd = 0
    if sdate.year == bdate.year:
        if start_m == bill_m:  # SAME MONTH
            tbd = number_of_day_in_bill_month - start_day + 1  # CASE 1
        elif start_m + 1 == bill_m and start_day >= bill_day:
            tbd = number_of_day_in_bill_month + (number_of_day_in_start_month - start_day + 1)  # CASE 2
        else:
            tbd = tbd = number_of_day_in_bill_month  # ONGOING CASE
    else:
        if (start_m == 12) and (sdate.year + 1 == bdate.year) and (bill_m == 1) and (
                start_day >= bill_day):  # DECEMBER/YEAR CHANGE
            tbd = number_of_day_in_bill_month + (number_of_day_in_start_month - start_day + 1)  # CASE 3
        else:
            tbd = number_of_day_in_bill_month  # ONGOING CASE

    # -----------------------------------------------------------------------------------

    # ADJUST CERTAIN VALUES IN PRELIM. BILL OBJECT
    const = decimal.Decimal((tbd / nodbm))

    room_cost = room_cost * const
    room_acc_cost = room_acc_cost * const
    com_ser_cost = com_ser_cost * const
    oth_ser_cost = oth_ser_cost * const
    adj = adj * const

    total = (room_cost + room_acc_cost + adj) + elec_cost + water_cost + (
            com_ser_cost + oth_ser_cost) + ovd_amt + late_f + maint_c

    # CREATE FINAL BILL OBJECT *******************
    new_bill = Billing(bill_ref=bref,
                       tenant_name=tname,
                       room_no=rno,
                       room_cost=room_cost,
                       room_acc_cost=room_acc_cost,
                       electricity_cost=elec_cost,
                       water_cost=water_cost,
                       common_ser_cost=com_ser_cost,
                       other_ser_cost=oth_ser_cost,
                       overdue_amount=ovd_amt,

                       # -----------------------
                       late_fee=late_f,
                       maint_cost=maint_c,
                       # -----------------------

                       adjust=adj,
                       bill_total=total,

                       )

    # SAVE BILL OBJECT TO DB
    new_bill.save()


@login_required
def billing(request):
    cur_date = datetime.datetime.now().date()

    current_dt = datetime.datetime.now().date()

    tenant_pf = TenantProfile.objects.filter(start_date__lt=cur_date).order_by("room_no")

    total_tn = len(tenant_pf)

    tpf_billForm_list = []
    for i in tenant_pf:
        rmn = i.room_no.room_no

        prefix = 'RM' + rmn  # RM101A etc.

        tpf_billForm_list.append((i, BillForm(prefix=prefix)))  # [(tpf,bf),(tpf,bf), ....]

    no_of_bill = 0

    if request.method == 'POST':
        for tpf in tenant_pf:

            rmn = tpf.room_no.room_no
            prefix = "RM" + rmn

            bill_form = BillForm(data=request.POST, instance=tpf, prefix=prefix)

            if bill_form.is_valid():

                bill_form.save(commit=True)
                # ------------------
                create_bill(rmn)
                no_of_bill += 1
                # ------------------
            else:
                messages.error(request, 'Error updating Room {} Billing'.format(rmn))

        messages.success(request, 'Total {} bills have been created.'.format(no_of_bill))

        return HttpResponseRedirect(reverse_lazy('admin_page'))

    else:

        return render(request, 'my_app/billing.html',
                      {
                          'tenant_pf': tenant_pf,
                          'section': 'billing',
                          'current_dt': current_dt,
                          'total_tn': total_tn,

                          'tpf_billForm_list': tpf_billForm_list
                      })


# @login_required (cannot be used here !!!)
def update_pf_and_bill(roomno, cd):
    pf = get_object_or_404(TenantProfile, room_no__room_no=roomno)
    bill = get_object_or_404(Billing, room_no=roomno, status='open')

    cf = bill.bill_total - cd['payment_amount']
    bill.cf_amount = cf
    pf.cum_ovd = cf
    bill.payment_date = cd['payment_date']
    bill.payment_amount = cd['payment_amount']
    bill.status = 'close'

    # CALCULATE LATE-FEE COST TO UPDATE PF.LATE_FEE
    bill_month = bill.bill_date.month

    pay_month = bill.payment_date.month
    pay_day = bill.payment_date.day

    late_fee = 0

    if pay_month > bill_month:
        if pay_day > GV.LATE_DAY_MAX:
            late_fee = GV.LATE_FEE_PER_DAY * (pay_day - GV.LATE_DAY_MAX)

    # Update pf for next billing
    pf.late_fee = late_fee

    # Update DB
    bill.save()
    pf.save()


@login_required
def month_bills(request):
    bills = Billing.objects.filter(status='open').order_by('id')


    open_bill_date = ""
    if bills:
        open_bill_date = bills[0].bill_date

    # -------------------------------------------------------------

    # return render(request, 'my_app/payment_individual.html', # old ver
    return render(request, 'my_app/month_bills.html',
                  {'bills': bills,
                   'section': 'month_bills',
                   # 'bill_month_year': bill_m_y,
                   'open_bill_date': open_bill_date
                   })


@login_required
def pay_bill(request, bref):
    tenant_bill = get_object_or_404(Billing, bill_ref=bref, status='open')
    rmn = tenant_bill.room_no

    if request.method == 'POST':
        pay_form = PaymentForm(data=request.POST)

        if pay_form.is_valid():
            cd = pay_form.cleaned_data
            # --------------------------
            update_pf_and_bill(rmn, cd)
            # --------------------------
        else:
            messages.error(request, 'Error updating Room {} Payment'.format(tenant_bill.room_no))
    else:
        pay_form = PaymentForm()  # Blank form

    if request.method == 'POST':
        messages.success(request, 'Room {} payment has been completed.'.format(rmn))
        return HttpResponseRedirect(reverse_lazy('month_bills'))
    else:
        return render(request, 'my_app/pay_bill.html', {'tenant_bill': tenant_bill, 'pay_form': pay_form})


@login_required
def report_type(request):
    return render(request, 'my_app/report_type.html', {'section': 'report'})


@login_required
def report_parameters(request):
    return render(request, 'my_app/report_parameters.html', {'section': 'report'})


@login_required
def monthly_report(request):
    bld = request.POST['bld']
    if bld == 'AB':
        bld = 'A&B'

    mnth = int(request.POST['month'])
    mnth_name = get_eng_month_name(mnth)
    yr = int(request.POST['year'])

    current_date_time = datetime.datetime.now()

    no_of_day_in_cur_month = calendar.monthrange(yr, mnth)[1]

    start_date = datetime.datetime(yr, mnth, 1)
    end_date = datetime.datetime(yr, mnth, no_of_day_in_cur_month)
    start_date = start_date.date()
    end_date = end_date.date()

    opl_a = Billing.objects.filter(status='close', room_no__endswith='A',
                                   bill_date__range=(start_date, end_date)).order_by('room_no')

    opl_b = Billing.objects.filter(status='close', room_no__endswith='B',
                                   bill_date__range=(start_date, end_date)).order_by('room_no')

    opl_a = list(opl_a)
    opl_b = list(opl_b)
    opl_ab = opl_a + opl_b

    trcac = 0
    tec = 0
    twc = 0
    tcsc = 0
    tosc = 0
    tovd = 0
    tlf_ma = 0
    tbt = 0
    tpa = 0

    all_bills_list = []
    total_amt_list = []

    if bld == 'A':
        all_bills_list = opl_a
    if bld == 'B':
        all_bills_list = opl_b
    if bld == 'A&B':
        all_bills_list = opl_ab

    for bill in all_bills_list:
        trcac += (bill.room_cost + bill.room_acc_cost + bill.adjust)
        tec += bill.electricity_cost
        twc += bill.water_cost
        tcsc += bill.common_ser_cost
        tosc += bill.other_ser_cost
        tovd += bill.overdue_amount
        tlf_ma += (bill.late_fee + bill.maint_cost)
        tbt += bill.bill_total
        tpa += bill.payment_amount
    total_amt_list = [trcac, tec, twc, tcsc, tosc, tovd, tlf_ma, tbt, tpa]

    return render(request, 'my_app/monthly_report.html',
                  {
                      'total_amt_list': total_amt_list,
                      'all_bills_list': all_bills_list,

                      'current_date_time': current_date_time,
                      'bld': bld,
                      'mnth_name': mnth_name,
                      'yr': yr,

                      'trcac': trcac,
                      'tec': tec,
                      'twc': twc,
                      'tcsc': tcsc,
                      'tosc': tosc,
                      'tovd': tovd,
                      'tlf_ma': tlf_ma,
                      'tbt': tbt,
                      'tpa': tpa

                  })


@login_required
def extra_rates(request):
    extra = Extra.objects.all().order_by('id')

    current_dt = datetime.datetime.now()

    # return render(request, 'my_app/extra_service.html', {'extra': extra, 'current_dt': current_dt})

    return render(request, 'my_app/extra_rates.html', {'extra': extra, 'current_dt': current_dt})


@login_required
def elec_cpu_change(request):
    if request.method == 'POST':
        elec_cpu_form = Elec_cpu_change(request.POST)
        if elec_cpu_form.is_valid():
            cd = elec_cpu_form.cleaned_data

            ex_item = get_object_or_404(Extra, desc='Electricity CPU')
            ex_item.cpu = cd['elec_cpu']
            ex_item.save()

            messages.info(request, 'Electricity CPU has been chnaged !!')

            return HttpResponseRedirect(reverse_lazy('admin_page'))
        else:
            messages.ERROR(request, 'Error ... !!')
    else:
        elec_cpu_form = Elec_cpu_change()
    return render(request, 'my_app/elec_cpu_change.html', {'elec_cpu_form': elec_cpu_form})


@login_required
def water_cpu_change(request):
    if request.method == 'POST':
        water_cpu_form = Water_cpu_change(request.POST)
        if water_cpu_form.is_valid():
            cd = water_cpu_form.cleaned_data

            ex_item = get_object_or_404(Extra, desc='Water CPU')
            ex_item.cpu = cd['water_cpu']
            ex_item.save()

            messages.success(request, 'Water CPU has been chnaged !!')
            return HttpResponseRedirect(reverse_lazy('admin_page'))
        else:
            messages.ERROR(request, 'Error ... !!')
    else:
        water_cpu_form = Water_cpu_change()
    return render(request, 'my_app/water_cpu_change.html', {'water_cpu_form': water_cpu_form})


@login_required
def room_type_rate(request):
    rm_type_rate = Room_type.objects.all()
    current_dt = datetime.datetime.now()

    return render(request, 'my_app/room_type_rate.html', {'rm_type_rate': rm_type_rate, 'current_dt': current_dt})


@login_required
def current_tenants(request):
    cur_tenant_pfs = TenantProfile.objects.all().order_by('start_date')

    total_tn = cur_tenant_pfs.count()

    current_dt = datetime.datetime.now()

    return render(request, 'my_app/current_tenants.html',
                  {
                      'cur_tenant_pfs': cur_tenant_pfs,
                      'current_dt': current_dt,
                      'total_tn': total_tn
                  })


@login_required
def vacant_rooms(request):
    current_dt = datetime.datetime.now()

    all_room = Room.objects.all()
    cur_tn = TenantProfile.objects.all()
    oc_rm_set = []
    vac_rm_set = []
    for tn in cur_tn:
        oc_rm_set.append(tn.room_no.room_no)

    for rm in all_room:
        if rm.room_no not in oc_rm_set:
            vac_rm_set.append(rm.room_no)

    no_of_vac_room = len(vac_rm_set)

    return render(request, 'my_app/vacant_rooms.html',
                  {'vac_rm_set': vac_rm_set, 'current_dt': current_dt, 'no_of_vac_room': no_of_vac_room})


@login_required
def misc_contents(request):
    return render(request, 'my_app/misc_contents.html', {'section': 'misc'})


@login_required
def manage_users(request):
    return render(request, 'my_app/manage_users.html')


class Register(generic.CreateView):
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('register_done')
    template_name = 'registration/register.html'


def register_done(request):
    return render(request, 'registration/register_done.html')


@login_required
def change_password(request):
    return render(request, 'my_app/change_password.html')


@login_required
def user_list_to_delete(request):
    query_set_tenantprofile, sorted_normal_tenantprofile_dict = list_existing_users(request)

    current_date_time = datetime.datetime.now()

    return render(request, 'my_app/user_list_to_delete.html',
                  {'tenantprofiles': query_set_tenantprofile, 'dict': sorted_normal_tenantprofile_dict,
                   'current_date_time': current_date_time})


@login_required
def confirm_delete_user(request, k):
    tprofile = TenantProfile.objects.get(room_no__room_no=k)

    rmn = tprofile.room_no.room_no
    name = tprofile.tenant.first_name + " " + tprofile.tenant.last_name

    return render(request, 'my_app/confirm_delete_users.html', {'rmn': rmn, 'name': name})


@login_required
def delete_user(request, rmn):
    tprofile = TenantProfile.objects.get(room_no__room_no=rmn)
    user = tprofile.tenant
    user.delete()

    current_date_time = datetime.datetime.now()

    query_set_tenantprofile, sorted_normal_tenantprofile_dict = list_existing_users(request)

    return render(request, 'my_app/user_list_to_delete.html',
                  {'tenantprofiles': query_set_tenantprofile, 'dict': sorted_normal_tenantprofile_dict,
                   'current_date_time': current_date_time})


def list_existing_users(request):
    query_set_tenantprofile = TenantProfile.objects.all()

    org_tenantprofile_dict = {}

    for i in query_set_tenantprofile:
        name = i.tenant.first_name + " " + i.tenant.last_name
        rmn = i.room_no.room_no
        phone = i.phone
        name_phone = name + " " + '(' + phone + ')'
        org_tenantprofile_dict.update({rmn: name_phone})  # {'105A': 'Ratchada R.', ....}

    org_keys_list = list(org_tenantprofile_dict.keys())  # 105A

    reversed_keys_list = []  # 105A --> A105
    for i in org_keys_list:
        reversed_keys_list.append(i[3:4] + i[0:3])

    reversed_tenantprofile_dict = {}  # {'A105': 'Ratchada R.', ....}
    org_vals_list = list(org_tenantprofile_dict.values())

    for i in range(0, len(org_keys_list)):
        reversed_tenantprofile_dict.update({reversed_keys_list[i]: org_vals_list[i]})

    reversed_keys_list = list(reversed_tenantprofile_dict.keys())
    reversed_keys_list.sort()

    sorted_reversed_dict = {}

    sorted_reversed_dict.update({i: reversed_tenantprofile_dict[i] for i in reversed_keys_list})

    sorted_reversed_keys_list = list(sorted_reversed_dict.keys())
    sorted_reversed_vals_list = list(sorted_reversed_dict.values())

    normal_keys_list = []  # A105 --> 105A

    for i in sorted_reversed_keys_list:
        normal_keys_list.append(i[1:] + i[0:1])

    sorted_normal_tenantprofile_dict = {}  # {'105A': 'Ratchada R.', ....}
    for i in range(0, len(sorted_reversed_keys_list)):
        sorted_normal_tenantprofile_dict.update({normal_keys_list[i]: sorted_reversed_vals_list[i]})

    return query_set_tenantprofile, sorted_normal_tenantprofile_dict


def maintenance_charge(request):
    if request.method == 'POST':

        maintenance_form = MaintenanceForm(data=request.POST)

        if maintenance_form.is_valid():

            cd = maintenance_form.cleaned_data

            # Create a new object but avoid saving it yet
            new_ma_charge = maintenance_form.save(commit=False)

            new_ma_charge.desc = 'Maintenance cost'

            # Save the new object(MaintenanceCharge) to DB for ref.
            new_ma_charge.save()

            rmn = cd['room_no']
            pf = get_object_or_404(TenantProfile, room_no__room_no=rmn)

            # INCREAMENT & SAVE VALUE TO PF.MAINT_COST
            pf.maint_cost += cd['job_cost']
            pf.save()

            messages.success(request, 'Maintenance cost has been charged to Room: {}.'.format(rmn))

            return HttpResponseRedirect(reverse_lazy('admin_page'))
        else:
            messages.error(request, 'Error: new record was not saved !!!')

    else:
        maintenance_form = MaintenanceForm()

    return render(request, 'my_app/maintenanace_charge.html', {'maintenance_form': maintenance_form})


@login_required
def new_tenant(request):
    tenant_name = str(request.user)

    return render(request, 'my_app/new_tenant.html', {'tenant_name': tenant_name})


@login_required
def tenant_profile(request):
    usr = str(request.user)
    fn, ln = usr.split(" ")
    # tenant_pf = get_object_or_404(TenantProfile, tenant__first_name=fn, tenant__last_name=ln)
    try:
        tenant_pf = TenantProfile.objects.get(tenant__first_name=fn, tenant__last_name=ln)
    except Exception as err:
        messages.error(request, 'ERROR: {} '.format(str(err)))
        return HttpResponseRedirect(reverse_lazy('login'))
    else:
        exd = {}
        exd.setdefault('Electricity CPU', 0)
        exd.setdefault('Water CPU', 0)
        exd.setdefault('Garbage', 0)
        exd.setdefault('Parking', 0)
        exd.setdefault('Wifi', 0)
        exd.setdefault('Cable TV', 0)
        exd.setdefault('Bed', 0)
        exd.setdefault('Bed accessories', 0)
        exd.setdefault('Dressing Table', 0)
        exd.setdefault('Clothing Cupboard', 0)
        exd.setdefault('TV Table', 0)
        exd.setdefault('Fridge', 0)
        exd.setdefault('Air-Conditioner', 0)

        for e in tenant_pf.extra.all():
            exd.update({e.desc: e.cpu})

        room_acc_cost = exd['Bed'] + exd['Bed accessories'] + exd['Dressing Table'] \
                        + exd['Clothing Cupboard'] + exd['TV Table'] + exd['Fridge'] \
                        + exd['Air-Conditioner']

        oth_ser_cost = exd['Garbage'] + exd['Parking'] + exd['Wifi'] + exd['Cable TV']

        cur_dt = datetime.datetime.now()

        return render(request, 'my_app/tenant_profile.html',
                      {'section': 'tenant_profile', 'tenant_pf': tenant_pf, 'room_acc_cost': room_acc_cost,
                       'oth_ser_cost': oth_ser_cost, 'cur_dt': cur_dt})


def tenant_bill_subroutine(tn_bill):
    bill_dt = tn_bill.bill_date
    pay_date = tn_bill.payment_date
    cur_mth = bill_dt.month
    cur_yr = bill_dt.year
    cur_th_mth = get_thai_month_name(str(bill_dt))
    cur_th_yr = get_thai_year(str(bill_dt))

    next_th_yr = cur_th_yr

    if cur_mth + 1 > 12:

        next_mth = 1
        next_yr = cur_yr + 1

        new_dt = datetime.date(next_yr, next_mth, 15)

        next_dt_mth = datetime.date(next_yr, next_mth, 15)

        next_th_yr = get_thai_year(str(new_dt))

    else:
        next_dt_mth = datetime.date(cur_yr, cur_mth + 1, 15)

    next_th_m = get_thai_month_name(str(next_dt_mth))

    room_with_acc_cost = tn_bill.room_cost + tn_bill.room_acc_cost + tn_bill.adjust

    pay_amt = tn_bill.payment_amount

    bill_misc = tn_bill.late_fee + tn_bill.maint_cost

    if tn_bill.status == 'open':
        paid_str = 'รอชำระ'
    else:
        paid_str = 'ชำระแล้ว ณ วันที่ {0} {1} {2} จำนวน {3:,.0f} บาท'.format(pay_date.day,
                                                                             get_thai_month_name(str(pay_date)),
                                                                             get_thai_year(str(pay_date)), pay_amt)

    # TEMPORARY UNTIL OVD OF RM204A HAS BEEN COVERED
    rn = tn_bill.room_no
    if rn == '204A':
        bill_total = tn_bill.bill_total
    else:
        bill_total = tn_bill.bill_total

    return room_with_acc_cost, bill_misc, bill_total, paid_str, cur_th_mth, next_th_m, cur_th_yr, next_th_yr


@login_required
def tenant_bill(request):
    tenant = str(request.user)
    bills = Billing.objects.filter(tenant_name=tenant)

    latest_bill_date = bills.order_by('bill_date')[0].bill_date

    latest_bill_date_thai_month = get_thai_month_name(str(latest_bill_date))
    latest_bill_date_thai_year = get_thai_year(str(latest_bill_date))

    if bills:
        tnb_qs = Billing.objects.filter(tenant_name=tenant, status='open')
        if tnb_qs:
            tn_bill = get_object_or_404(Billing, tenant_name=tenant, status='open')


        else:
            bill_month = str(datetime.datetime.now().month)
            tnb_qs = Billing.objects.filter(tenant_name=tenant, status='close', bill_date__month=bill_month)
            if tnb_qs:
                tn_bill = get_object_or_404(Billing, tenant_name=tenant, status='close', bill_date__month=bill_month)
            else:
                bill_month = str(datetime.datetime.now().month - 1)
                tn_bill = get_object_or_404(Billing, tenant_name=tenant, status='close', bill_date__month=bill_month)

        room_with_acc_cost, bill_misc, bill_total, paid_str, cur_th_mth, next_th_m, cur_th_yr, next_th_yr = tenant_bill_subroutine(
            tn_bill)

        return render(request, 'my_app/tenant_bill.html',
                      {'section': 'tenant_bill', 'tn_bill': tn_bill, 'room_with_acc_cost': room_with_acc_cost,
                       'bill_misc': bill_misc, 'bill_total': bill_total, 'cur_th_mth': cur_th_mth,
                       'next_th_m': next_th_m,
                       'cur_th_yr': cur_th_yr, 'next_th_yr': next_th_yr, 'paid_str': paid_str,
                       'latest_bill_date': latest_bill_date,
                       'latest_bill_date_thai_month':latest_bill_date_thai_month,
                       'latest_bill_date_thai_year':latest_bill_date_thai_year,
                       })

    else:
        # NEW TENANT
        return HttpResponseRedirect(reverse_lazy('new_tenant'))


def tenant_feedback(request):
    return render(request, 'my_app/tenant_feedback.html', {'section': 'tenant_feedback'})


def get_ref_string():
    char_str = list('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
    random.shuffle(char_str)
    fd = random.choice(char_str)

    sd = str(random.randint(0, 9)) + str(random.randint(0, 9)) + str(random.randint(0, 9)) + str(
        random.randint(0, 9))
    ref_str = fd + '-' + sd

    return ref_str


def get_eng_month_name(m: int):
    md = {1: 'January', 2: 'February', 3: 'March', 4: 'April', 5: 'May', 6: 'June', 7: 'July', 8: 'August',
          9: 'September',
          10: 'October', 11: 'November', 12: 'December'}
    im = int(m)
    return md[im]


def get_thai_month_name(bill_date: str):
    md = {1: 'มกราคม', 2: 'กุมภาพันธ์', 3: 'มีนาคม', 4: 'เมษายน', 5: 'พฤษภาคม', 6: 'มิถุนายน', 7: 'กรกฏาคม',
          8: 'สิงหาคม', 9: 'กันยายน',
          10: 'ตุลาคม', 11: 'พฤศจิกายน', 12: 'ธันวาคม'}

    y, m, d = bill_date.split('-')

    im = int(m)
    return md[im]


def get_thai_year(bill_date: str):
    y, m, d = bill_date.split('-')

    christ_y = int(y)
    buddist_y = christ_y + 543

    return str(buddist_y)


def make_date_string(self, ds: str):
    y, m, d = str(ds).split('-')
    return d + '-' + m + '-' + y


def give_error_message(error_msg):
    print(error_msg)


def give_info_message(error_msg):
    print(error_msg)


def get_aware_datetime(date_str):
    ret = parse_datetime(date_str)
    if not is_aware(ret):
        ret = make_aware(ret)
    return ret
