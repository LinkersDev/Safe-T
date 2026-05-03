import { useState, type FormEvent } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Card } from '../../../shared/components/ui/Card'
import { Input } from '../../../shared/components/ui/Input'
import { Button } from '../../../shared/components/ui/Button'
import { StatusNoticeCard } from '../../../shared/components/ui/StatusNoticeCard'
import { useToast } from '../../../shared/components/ui/Toast'
import { normalizeApiError } from '../../../core/api/error-normalizer'
import { registerStaff } from '../../staff/services/staff-service'

const SELECT_CLASS =
  'min-h-[44px] w-full rounded-md border border-border bg-surface-primary px-3 py-2 text-sm text-text-primary outline-none transition-colors focus:border-brand-primary'

const DEPARTMENTS = ['Operations', 'Customer Service', 'Risk', 'IT', 'Finance', 'Compliance', 'HR'] as const
const BRANCHES = ['HARGEISA', 'BERBERA', 'BURAO', 'BORAMA', 'ERIGAVO'] as const
const JOB_TITLES = [
  'System Admin',
  'Teller',
  'Teller Admin',
  'Customer Service Officer',
  'Risk Officer',
  'IT Support',
  'Finance Officer',
] as const
const CITIES = ['HARGEISA', 'BERBERA', 'BURAO', 'BORAMA', 'ERIGAVO'] as const
const COUNTRIES = ['Somaliland', 'Somalia', 'Ethiopia', 'Djibouti', 'Kenya', 'Uganda'] as const
const OTHER = '__OTHER__' as const

export function StaffRegisterStaffPage() {
  const toast = useToast()

  const [fullName, setFullName] = useState('')
  const [phoneNumber, setPhoneNumber] = useState('')
  const [roleCode, setRoleCode] = useState<'ADMIN' | 'TELLER' | 'TELLER_ADMIN' | 'CUSTOMER_SERVICE' | 'RISK_OFFICER'>('CUSTOMER_SERVICE')

  const [employeeId, setEmployeeId] = useState('')
  const [department, setDepartment] = useState<(typeof DEPARTMENTS)[number] | '' | typeof OTHER>('')
  const [departmentOther, setDepartmentOther] = useState('')
  const [branch, setBranch] = useState<(typeof BRANCHES)[number] | '' | typeof OTHER>('')
  const [branchOther, setBranchOther] = useState('')
  const [jobTitle, setJobTitle] = useState<(typeof JOB_TITLES)[number] | '' | typeof OTHER>('')
  const [jobTitleOther, setJobTitleOther] = useState('')

  const [addressLine1, setAddressLine1] = useState('')
  const [addressCity, setAddressCity] = useState<(typeof CITIES)[number] | '' | typeof OTHER>('')
  const [addressCityOther, setAddressCityOther] = useState('')
  const [addressCountry, setAddressCountry] = useState<(typeof COUNTRIES)[number] | '' | typeof OTHER>('')
  const [addressCountryOther, setAddressCountryOther] = useState('')

  const [result, setResult] = useState<{ next_step?: string } | null>(null)

  const mutation = useMutation({
    mutationFn: registerStaff,
    onSuccess: (data) => {
      toast.success('Staff user created.')
      setResult({ next_step: data?.onboarding?.next_step })
      setFullName('')
      setPhoneNumber('')
      setRoleCode('CUSTOMER_SERVICE')
      setEmployeeId('')
      setDepartment('')
      setDepartmentOther('')
      setBranch('')
      setBranchOther('')
      setJobTitle('')
      setJobTitleOther('')
      setAddressLine1('')
      setAddressCity('')
      setAddressCityOther('')
      setAddressCountry('')
      setAddressCountryOther('')
    },
    onError: (err) => {
      const normalized = normalizeApiError(err)
      toast.error(normalized.detail)
    },
  })

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    const departmentValue = department === OTHER ? departmentOther.trim() : String(department).trim()
    const branchValue = branch === OTHER ? branchOther.trim() : String(branch).trim()
    const jobTitleValue = jobTitle === OTHER ? jobTitleOther.trim() : String(jobTitle).trim()
    const cityValue = addressCity === OTHER ? addressCityOther.trim() : String(addressCity).trim()
    const countryValue = addressCountry === OTHER ? addressCountryOther.trim() : String(addressCountry).trim()

    mutation.mutate({
      full_name: fullName.trim(),
      phone_number: phoneNumber.trim(),
      role_code: roleCode,
      employee_id: employeeId.trim() || undefined,
      department: departmentValue || undefined,
      branch: branchValue || undefined,
      job_title: jobTitleValue || undefined,
      address_line1: addressLine1.trim() || undefined,
      address_city: cityValue || undefined,
      address_country: countryValue || undefined,
    })
  }

  return (
    <div className="max-w-3xl space-y-4">
      <Card as="form" className="space-y-4" onSubmit={onSubmit}>
        <div>
          <p className="text-sm font-semibold text-text-primary">Register staff user</p>
          <p className="mt-0.5 text-xs text-text-tertiary">
            Staff will complete first login using OTP (set password + PIN).
          </p>
        </div>

        <div className="grid gap-3 md:grid-cols-3">
          <div className="md:col-span-2">
            <label className="mb-1 block text-xs font-medium text-text-secondary">Full name</label>
            <Input value={fullName} onChange={(e) => setFullName(e.target.value)} required />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-text-secondary">Phone</label>
            <Input inputMode="tel" placeholder="+252…" value={phoneNumber} onChange={(e) => setPhoneNumber(e.target.value)} required />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-text-secondary">Role</label>
            <select value={roleCode} onChange={(e) => setRoleCode(e.target.value as any)} className={SELECT_CLASS} required>
              <option value="ADMIN">ADMIN</option>
              <option value="TELLER">TELLER</option>
              <option value="TELLER_ADMIN">TELLER_ADMIN</option>
              <option value="CUSTOMER_SERVICE">CUSTOMER_SERVICE</option>
              <option value="RISK_OFFICER">RISK_OFFICER</option>
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-text-secondary">Employee ID</label>
            <Input placeholder="Optional" value={employeeId} onChange={(e) => setEmployeeId(e.target.value)} />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-text-secondary">Department</label>
            <select value={department} onChange={(e) => setDepartment(e.target.value as any)} className={SELECT_CLASS}>
              <option value="">Select…</option>
              {DEPARTMENTS.map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
              <option value={OTHER}>Other…</option>
            </select>
          </div>
          {department === OTHER && (
            <div>
              <label className="mb-1 block text-xs font-medium text-text-secondary">Department (custom)</label>
              <Input placeholder="Type department" value={departmentOther} onChange={(e) => setDepartmentOther(e.target.value)} />
            </div>
          )}

          <div>
            <label className="mb-1 block text-xs font-medium text-text-secondary">Branch</label>
            <select value={branch} onChange={(e) => setBranch(e.target.value as any)} className={SELECT_CLASS}>
              <option value="">Select…</option>
              {BRANCHES.map((b) => (
                <option key={b} value={b}>{b}</option>
              ))}
              <option value={OTHER}>Other…</option>
            </select>
          </div>
          {branch === OTHER && (
            <div>
              <label className="mb-1 block text-xs font-medium text-text-secondary">Branch (custom)</label>
              <Input placeholder="Type branch" value={branchOther} onChange={(e) => setBranchOther(e.target.value)} />
            </div>
          )}
          <div className="md:col-span-2">
            <label className="mb-1 block text-xs font-medium text-text-secondary">Job title</label>
            <select value={jobTitle} onChange={(e) => setJobTitle(e.target.value as any)} className={SELECT_CLASS}>
              <option value="">Select…</option>
              {JOB_TITLES.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
              <option value={OTHER}>Other…</option>
            </select>
          </div>
          {jobTitle === OTHER && (
            <div className="md:col-span-2">
              <label className="mb-1 block text-xs font-medium text-text-secondary">Job title (custom)</label>
              <Input placeholder="Type job title" value={jobTitleOther} onChange={(e) => setJobTitleOther(e.target.value)} />
            </div>
          )}
        </div>

        <div className="border-t border-border pt-4">
          <p className="text-xs font-semibold text-text-secondary">Address (optional)</p>
          <div className="mt-3 grid gap-3 md:grid-cols-3">
            <div className="md:col-span-2">
              <label className="mb-1 block text-xs font-medium text-text-secondary">Address line 1</label>
              <Input placeholder="Street / area" value={addressLine1} onChange={(e) => setAddressLine1(e.target.value)} />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-text-secondary">City</label>
              <select value={addressCity} onChange={(e) => setAddressCity(e.target.value as any)} className={SELECT_CLASS}>
                <option value="">Select…</option>
                {CITIES.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
                <option value={OTHER}>Other…</option>
              </select>
            </div>
            {addressCity === OTHER && (
              <div>
                <label className="mb-1 block text-xs font-medium text-text-secondary">City (custom)</label>
                <Input placeholder="Type city" value={addressCityOther} onChange={(e) => setAddressCityOther(e.target.value)} />
              </div>
            )}
            <div>
              <label className="mb-1 block text-xs font-medium text-text-secondary">Country</label>
              <select value={addressCountry} onChange={(e) => setAddressCountry(e.target.value as any)} className={SELECT_CLASS}>
                <option value="">Select…</option>
                {COUNTRIES.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
                <option value={OTHER}>Other…</option>
              </select>
            </div>
            {addressCountry === OTHER && (
              <div>
                <label className="mb-1 block text-xs font-medium text-text-secondary">Country (custom)</label>
                <Input placeholder="Type country" value={addressCountryOther} onChange={(e) => setAddressCountryOther(e.target.value)} />
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center justify-end gap-2">
          <Button loading={mutation.isPending} type="submit" variant="secondary">
            Create staff user
          </Button>
        </div>
      </Card>

      {result?.next_step && (
        <StatusNoticeCard
          title="Staff created"
          message={result.next_step}
          variant="info"
        />
      )}
    </div>
  )
}

